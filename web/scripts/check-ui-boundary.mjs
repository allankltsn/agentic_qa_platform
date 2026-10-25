import { readdirSync, readFileSync, statSync } from 'node:fs';
import ts from 'typescript';
import { join, relative, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const ALLOWED = [/^src\/components\/ui\//, /^src\/brand\//, /^src\/test\//, /\.(test|stories)\.tsx?$/];
const HEX = /#[0-9a-fA-F]{3,8}\b/;
const FORBIDDEN_IMPORT = /^(react-aria-components|@radix-ui\/|@allankltsn\/ui)/;
const NON_SEMANTIC_COLOR = /(?:bg|text|border|ring|fill|stroke)-(?:red|blue|green|gray|slate|zinc|neutral|white|black)(?:-\d+)?\b/;

export function findViolations(relPath, content) {
  const p = relPath.split(sep).join('/').replaceAll('\\', '/');
  if (ALLOWED.some((re) => re.test(p))) return [];
  const violations = new Set();
  const add = (message) => violations.add(`${p}: ${message}`);
  if (!p.startsWith('src/')) return [];
  if (HEX.test(content)) add('cor hexadecimal fora de brand/ (use tokens)');
  if (/\.(css|scss)$/.test(p)) {
    if (p !== 'src/styles.css') add('CSS fora da base de UI');
    return [...violations];
  }

  const source = ts.createSourceFile(p, content, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);

  // --- Best-effort constant folding ---------------------------------------
  // Values built at runtime (string concatenation, template literals,
  // array.join()) can hide a hex color, a forbidden import specifier, or a
  // JSX tag name from the plain-text/literal checks below. This resolves the
  // common shapes seen in practice (QA adversarial probes) so the same
  // heuristics can be applied to the resolved value. It is NOT data-flow
  // analysis: reassignment, cross-module values, and non-literal inputs
  // (e.g. values from props/env/fetch) are not resolved and remain an
  // accepted residual risk — see check-ui-boundary.test.ts and
  // docs/sprints/evidence/sprint-03/task-14A-fix/ for the documented
  // rationale and what is deliberately left out.
  const stringVars = new Map();
  const arrayVars = new Map();
  const declarations = [];
  (function collect(node) {
    if (ts.isVariableDeclaration(node) && ts.isIdentifier(node.name) && node.initializer) {
      declarations.push(node);
    }
    ts.forEachChild(node, collect);
  })(source);

  function foldArray(node) {
    if (!node) return undefined;
    if (ts.isArrayLiteralExpression(node)) {
      const out = [];
      for (const el of node.elements) {
        const v = foldValue(el);
        if (v === undefined) return undefined;
        out.push(v);
      }
      return out;
    }
    if (ts.isIdentifier(node)) return arrayVars.get(node.text);
    return undefined;
  }

  function foldValue(node) {
    if (!node) return undefined;
    if (ts.isParenthesizedExpression(node)) return foldValue(node.expression);
    if (ts.isStringLiteralLike(node)) return node.text;
    if (ts.isNoSubstitutionTemplateLiteral(node)) return node.text;
    if (ts.isTemplateExpression(node)) {
      let out = node.head.text;
      for (const span of node.templateSpans) {
        const v = foldValue(span.expression);
        if (v === undefined) return undefined;
        out += v + span.literal.text;
      }
      return out;
    }
    if (ts.isBinaryExpression(node) && node.operatorToken.kind === ts.SyntaxKind.PlusToken) {
      const l = foldValue(node.left);
      const r = foldValue(node.right);
      return l === undefined || r === undefined ? undefined : l + r;
    }
    if (ts.isCallExpression(node) && ts.isPropertyAccessExpression(node.expression) && node.expression.name.text === 'join') {
      const arr = foldArray(node.expression.expression);
      if (arr === undefined) return undefined;
      const sepArg = node.arguments[0] ? foldValue(node.arguments[0]) : undefined;
      return arr.join(sepArg ?? ',');
    }
    if (ts.isIdentifier(node)) return stringVars.get(node.text);
    return undefined;
  }

  // Fixed-point over declarations: chains like `const parts = [...]; const
  // hex = '#' + parts.join('')` resolve regardless of declaration order.
  for (let i = 0; i < 3; i += 1) {
    for (const decl of declarations) {
      if (ts.isArrayLiteralExpression(decl.initializer)) {
        const arr = foldArray(decl.initializer);
        if (arr !== undefined) arrayVars.set(decl.name.text, arr);
      } else {
        const value = foldValue(decl.initializer);
        if (value !== undefined) stringVars.set(decl.name.text, value);
      }
    }
  }

  // A hex color or a forbidden import specifier reconstructed at runtime is
  // just as much a boundary violation as a literal one, even if we never see
  // where the resolved value is actually used.
  for (const value of stringVars.values()) {
    if (HEX.test(value)) add('cor hexadecimal reconstruída em runtime fora de brand/ (use tokens)');
    if (FORBIDDEN_IMPORT.test(value)) {
      add('valor reconstruído em runtime corresponde a um import de react-aria-components/@radix-ui/@allankltsn (importe primitivas locais de src/components/ui)');
    }
  }

  function isSuspiciousDynamicShape(node) {
    if (!node) return false;
    if (ts.isParenthesizedExpression(node)) return isSuspiciousDynamicShape(node.expression);
    if (ts.isBinaryExpression(node) && node.operatorToken.kind === ts.SyntaxKind.PlusToken) return true;
    if (ts.isTemplateExpression(node)) return true;
    if (ts.isCallExpression(node) && ts.isPropertyAccessExpression(node.expression) && node.expression.name.text === 'join') return true;
    if (ts.isIdentifier(node)) {
      const decl = declarations.find((d) => d.name.text === node.text);
      return decl ? isSuspiciousDynamicShape(decl.initializer) : false;
    }
    return false;
  }

  const visit = (node) => {
    if (ts.isStringLiteralLike(node) && FORBIDDEN_IMPORT.test(node.text)) add('importe primitivas locais de src/components/ui');

    // import()/require() with a non-literal argument built via
    // concatenation/template/join: cannot be proven safe statically.
    const isRequireCall = ts.isCallExpression(node) && ts.isIdentifier(node.expression) && node.expression.text === 'require';
    const isDynamicImport = ts.isCallExpression(node) && node.expression.kind === ts.SyntaxKind.ImportKeyword;
    if (isRequireCall || isDynamicImport) {
      const arg = node.arguments[0];
      if (arg && !ts.isStringLiteralLike(arg)) {
        const resolved = foldValue(arg);
        if (resolved !== undefined && FORBIDDEN_IMPORT.test(resolved)) {
          add('import/require dinâmico reconstrói um pacote proibido em runtime (use import estático de src/components/ui)');
        } else if (isSuspiciousDynamicShape(arg)) {
          add('import/require dinâmico com valor construído em runtime (concatenação/template/join) — revise manualmente');
        }
      }
    }

    if (ts.isJsxAttribute(node)) {
      const name = node.name.getText(source);
      if (name === 'style') add('style inline (use classes com tokens da marca)');
      if (name === 'className') {
        let text = node.getText(source);
        if (node.initializer && ts.isJsxExpression(node.initializer) && node.initializer.expression) {
          const folded = foldValue(node.initializer.expression);
          if (folded !== undefined) text = `className=${JSON.stringify(folded)}`;
        }
        if (NON_SEMANTIC_COLOR.test(text)) add('cor não semântica (use tokens)');
      }
    }

    if (!p.startsWith('src/layouts/') && (ts.isJsxOpeningElement(node) || ts.isJsxSelfClosingElement(node))) {
      const tagNode = node.tagName;
      const tagText = tagNode.getText(source);
      const isLiteralRawTag = /^[a-z]/.test(tagText);
      const isVariableTag = ts.isIdentifier(tagNode) && stringVars.has(tagText);
      if (isLiteralRawTag || isVariableTag) {
        const hasStyleAttr = node.attributes.properties.some((a) => ts.isJsxAttribute(a) && a.name.getText(source) === 'style');
        if (!hasStyleAttr) {
          add(isVariableTag
            ? 'elemento de UI dinâmico (nome de tag vem de uma variável) fora de components/ui, layouts ou brand'
            : 'elemento de UI fora de components/ui, layouts ou brand');
        }
      }
    }

    if (!p.startsWith('src/layouts/') && ts.isCallExpression(node) && /(?:^|\.)createElement$/.test(node.expression.getText(source))) {
      const arg0 = node.arguments[0];
      if (arg0 && ts.isStringLiteral(arg0)) add('elemento de UI fora de components/ui, layouts ou brand');
      else if (arg0 && ts.isIdentifier(arg0) && stringVars.has(arg0.text)) {
        add('elemento de UI dinâmico (createElement com variável) fora de components/ui, layouts ou brand');
      }
    }

    ts.forEachChild(node, visit);
  };
  visit(source);
  return [...violations];
}

function walk(dir) {
  return readdirSync(dir).flatMap((n) => {
    const f = join(dir, n);
    return statSync(f).isDirectory() ? walk(f) : [f];
  });
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const root = join(fileURLToPath(new URL('.', import.meta.url)), '..');
  const bad = walk(join(root, 'src'))
    .filter((f) => /\.(tsx?|css)$/.test(f))
    .flatMap((f) => findViolations(relative(root, f), readFileSync(f, 'utf8')));
  if (bad.length) { console.error(bad.join('\n')); process.exit(1); }
  console.log('ui boundary OK');
}

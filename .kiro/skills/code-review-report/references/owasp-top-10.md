# OWASP Top 10 — Referência para Code Review

Este documento serve como referência rápida para avaliação de segurança durante o code review.
Para informações atualizadas, sempre complemente com pesquisa web: `"OWASP Top 10 2021"` ou versão mais recente.

## A01:2021 — Broken Access Control

**O que é:** Falhas que permitem usuários agirem fora de suas permissões.

**O que procurar no código:**
- Endpoints sem verificação de autenticação/autorização
- Acesso direto a objetos por ID sem verificar ownership (IDOR)
- Falta de middleware de autorização em rotas sensíveis
- Elevação de privilégio por manipulação de parâmetros (role, is_admin)
- Acesso a APIs administrativas sem verificação de role
- CORS mal configurado (allow-origin: *)

**Exemplos por linguagem:**

PHP/Laravel:
```php
// VULNERÁVEL — sem verificação de ownership
Route::get('/user/{id}/data', function ($id) {
    return User::find($id)->sensitiveData;
});

// CORRETO
Route::get('/user/{id}/data', function ($id) {
    $user = User::findOrFail($id);
    $this->authorize('view', $user);
    return $user->sensitiveData;
});
```

Node.js/Express:
```javascript
// VULNERÁVEL
app.get('/api/orders/:id', (req, res) => {
    Order.findById(req.params.id).then(order => res.json(order));
});

// CORRETO
app.get('/api/orders/:id', authMiddleware, (req, res) => {
    Order.findOne({ _id: req.params.id, userId: req.user.id })
        .then(order => order ? res.json(order) : res.status(403).send());
});
```

Python/Django:
```python
# VULNERÁVEL
def get_document(request, doc_id):
    return Document.objects.get(id=doc_id)

# CORRETO
def get_document(request, doc_id):
    return get_object_or_404(Document, id=doc_id, owner=request.user)
```

---

## A02:2021 — Cryptographic Failures

**O que é:** Falhas na proteção de dados sensíveis em trânsito e em repouso.

**O que procurar no código:**
- Senhas armazenadas em texto plano ou com hash fraco (MD5, SHA1)
- Dados sensíveis transmitidos sem TLS/HTTPS
- Chaves de criptografia hardcoded no código
- Uso de algoritmos deprecated (DES, RC4, MD5 para hashing)
- Tokens/sessions sem expiração
- Dados sensíveis em logs ou mensagens de erro

**Sinais de alerta:**
```
md5(, sha1(, base64_encode( para senhas
http:// em URLs de API (sem TLS)
password = "..." em código
SECRET_KEY = "..." em código
```

---

## A03:2021 — Injection

**O que é:** Dados não confiáveis enviados a um interpretador como parte de um comando ou query.

**O que procurar no código:**
- SQL queries construídas com concatenação de strings
- Comandos shell com input do usuário
- LDAP queries com input não sanitizado
- XPath/XML queries com input não sanitizado
- ORM queries com raw SQL sem parametrização
- Template injection (SSTI)

**Exemplos por linguagem:**

PHP:
```php
// VULNERÁVEL — SQL Injection
$query = "SELECT * FROM users WHERE email = '" . $_POST['email'] . "'";

// CORRETO — Prepared statement
$stmt = $pdo->prepare("SELECT * FROM users WHERE email = ?");
$stmt->execute([$request->input('email')]);

// CORRETO — Eloquent ORM
User::where('email', $request->input('email'))->first();
```

Python:
```python
# VULNERÁVEL
cursor.execute(f"SELECT * FROM users WHERE email = '{email}'")

# CORRETO
cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
```

Node.js:
```javascript
// VULNERÁVEL
db.query(`SELECT * FROM users WHERE email = '${req.body.email}'`);

// CORRETO
db.query('SELECT * FROM users WHERE email = $1', [req.body.email]);
```

---

## A04:2021 — Insecure Design

**O que é:** Falhas de design que não podem ser corrigidas com implementação perfeita.

**O que procurar:**
- Falta de rate limiting em endpoints sensíveis (login, reset password, OTP)
- Ausência de validação de negócio (ex: preço negativo, quantidade absurda)
- Fluxos que permitem bypass de etapas (ex: pular verificação de email)
- Falta de separação de ambientes (dev/staging/prod)
- Ausência de threat modeling para funcionalidades críticas

---

## A05:2021 — Security Misconfiguration

**O que é:** Configurações de segurança ausentes, incorretas ou padrão.

**O que procurar no código:**
- Debug mode habilitado em produção (APP_DEBUG=true, DEBUG=True)
- Stack traces expostos em respostas de erro
- Headers de segurança ausentes (CSP, X-Frame-Options, HSTS)
- Diretórios listáveis
- Credenciais padrão não alteradas
- Permissões excessivas em arquivos/diretórios
- CORS permissivo demais

---

## A06:2021 — Vulnerable and Outdated Components

**O que é:** Uso de componentes com vulnerabilidades conhecidas.

**O que procurar:**
- Dependências desatualizadas (comparar com versões atuais)
- Dependências com CVEs conhecidos (pesquisar web)
- Dependências abandonadas (sem commits há mais de 1 ano)
- Falta de lock file (package-lock.json, composer.lock, Pipfile.lock)
- Ausência de ferramentas de auditoria (npm audit, composer audit, pip-audit)

**Como verificar:**
- Pesquisar: `"<pacote> <versão> CVE"` ou `"<pacote> vulnerability"`
- Verificar: https://nvd.nist.gov/, https://snyk.io/vuln/
- Comparar versão usada vs. versão mais recente

---

## A07:2021 — Identification and Authentication Failures

**O que é:** Falhas na confirmação de identidade e gerenciamento de sessão.

**O que procurar:**
- Falta de proteção contra brute force (rate limiting, account lockout)
- Senhas fracas permitidas (sem política de complexidade)
- Recuperação de senha insegura (tokens previsíveis, sem expiração)
- Sessões que não expiram ou não são invalidadas no logout
- Tokens JWT sem validação de assinatura ou com secret fraco
- Falta de MFA em operações sensíveis

---

## A08:2021 — Software and Data Integrity Failures

**O que é:** Falhas relacionadas a código e infraestrutura que não protegem contra violações de integridade.

**O que procurar:**
- Dependências de fontes não confiáveis sem verificação de integridade
- Pipelines CI/CD sem verificação de integridade
- Desserialização insegura de dados não confiáveis
- Auto-update sem verificação de assinatura

---

## A09:2021 — Security Logging and Monitoring Failures

**O que é:** Falta de logging e monitoramento adequados para detectar e responder a incidentes.

**O que procurar:**
- Eventos de login/logout não logados
- Falhas de autenticação não logadas
- Transações de alto valor sem audit trail
- Logs sem informação suficiente (timestamp, user, IP, ação)
- Dados sensíveis em logs (senhas, tokens, PII)
- Ausência de alertas para eventos suspeitos

---

## A10:2021 — Server-Side Request Forgery (SSRF)

**O que é:** Aplicação faz requisições a URLs fornecidas pelo usuário sem validação.

**O que procurar:**
- Funcionalidades que aceitam URLs do usuário (webhooks, importação, preview)
- Requisições HTTP server-side com URL controlada pelo usuário
- Falta de whitelist de domínios/IPs permitidos
- Acesso a metadados de cloud (169.254.169.254)

---

## Notas para o Revisor

1. **Adapte ao contexto**: Nem toda vulnerabilidade OWASP se aplica a todo projeto. Uma API interna tem perfil de risco diferente de uma aplicação pública.
2. **Pesquise atualizações**: O OWASP Top 10 é atualizado periodicamente. Use pesquisa web para verificar se há versão mais recente que 2021.
3. **Não seja alarmista**: Classifique a severidade considerando o contexto real de exposição do código.
4. **Priorize**: Injection e Broken Access Control em código público são mais urgentes que Security Misconfiguration em ambiente de desenvolvimento.

import type { Config } from 'tailwindcss';

const names = [
  'bg', 'surface', 'surface-2', 'line', 'line-strong', 'ink', 'muted', 'faint',
  'primary', 'primary-hover', 'primary-press', 'primary-soft', 'primary-line', 'on-primary', 'accent-text', 'accent',
  'success', 'success-bg', 'success-text', 'warning', 'warning-bg', 'warning-text',
  'danger', 'on-danger', 'danger-bg', 'danger-text', 'info', 'info-bg', 'info-text',
  'nav', 'nav-2', 'nav-line', 'nav-ink', 'nav-muted',
];

const colors = Object.fromEntries(names.map((n) => [n, `rgb(var(--color-${n}) / <alpha-value>)`]));

// [tamanho, altura de linha, peso]
const typography: Record<string, [number, number, number]> = {
  display: [30, 38, 700],
  'heading-lg': [24, 32, 700],
  'heading-md': [20, 28, 700],
  'heading-sm': [16, 24, 600],
  body: [14, 22, 400],
  'body-medium': [14, 22, 500],
  label: [13, 20, 600],
  caption: [12, 18, 400],
  kicker: [11, 16, 700],
  button: [14, 20, 600],
};

const fontSize = Object.fromEntries(
  Object.entries(typography).map(([n, [s, l, w]]) => [n, [`${s}px`, { lineHeight: `${l}px`, fontWeight: String(w) }]]),
) as NonNullable<NonNullable<Config['theme']>['fontSize']>;

export default {
  darkMode: 'class',
  content: [],
  theme: {
    extend: {
      colors,
      fontSize,
      borderRadius: { sm: '8px', md: '12px', lg: '16px' },
      boxShadow: {
        card: '0 1px 2px rgb(21 35 58 / 0.06), 0 1px 3px rgb(21 35 58 / 0.04)',
        dialog: '0 20px 50px rgb(11 23 40 / 0.3)',
      },
    },
  },
} satisfies Config;

import type { Config } from 'tailwindcss';
import brand from './src/brand/tailwind-preset';

export default {
  presets: [brand],
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: { extend: { fontFamily: { sans: ['"Inter Variable"', 'Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'] } } },
} satisfies Config;

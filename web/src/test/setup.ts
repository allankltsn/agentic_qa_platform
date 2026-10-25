import '@testing-library/jest-dom/vitest';
import { cleanup, configure } from '@testing-library/react';
import { afterEach } from 'vitest';

// As páginas são lazy: o primeiro render espera o import dinâmico.
configure({ asyncUtilTimeout: 5000 });

afterEach(() => { cleanup(); localStorage.clear(); });

// jsdom não tem PointerEvent; React Aria precisa de pointerType para interpretar cliques.
class TestPointerEvent extends MouseEvent {
  readonly pointerId: number;
  readonly pointerType: string;
  readonly isPrimary: boolean;
  constructor(type: string, init: PointerEventInit = {}) {
    super(type, init);
    this.pointerId = init.pointerId ?? 1;
    this.pointerType = init.pointerType ?? 'mouse';
    this.isPrimary = init.isPrimary ?? true;
  }
}
if (!window.PointerEvent) Object.defineProperty(window, 'PointerEvent', { value: TestPointerEvent });

// jsdom 25 não faz parse de @layer: neutraliza a injeção de estilos do React Aria nos testes.
const pressableStyles = document.createElement('style');
pressableStyles.id = 'react-aria-pressable-style';
document.head.append(pressableStyles);

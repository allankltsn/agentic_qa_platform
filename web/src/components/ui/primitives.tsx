import { createElement, forwardRef, type ComponentPropsWithoutRef, type ElementType, type ForwardRefExoticComponent, type RefAttributes } from 'react';
import { cn } from '@/lib/utils';

/**
 * Primitivas de estrutura: as páginas não usam tags HTML cruas (check:ui), só estes componentes. Cada uma é a tag
 * correspondente sem estilo próprio; o visual vem de classes com tokens da marca.
 */
function el<K extends keyof HTMLElementTagNameMap>(tag: K, name: string, extra?: Record<string, unknown>) {
  const Component = forwardRef<HTMLElementTagNameMap[K], ComponentPropsWithoutRef<K>>(function Primitive({ className, ...rest }, ref) {
    return createElement(tag as ElementType, { ...extra, ...rest, ref, className: cn(className as string | undefined) });
  });
  Component.displayName = name;
  return Component as ForwardRefExoticComponent<ComponentPropsWithoutRef<K> & RefAttributes<HTMLElementTagNameMap[K]>>;
}

export const Box = el('div', 'Box');
export const Section = el('section', 'Section');
export const Span = el('span', 'Span');
export const P = el('p', 'P');
export const Strong = el('strong', 'Strong');
export const Em = el('em', 'Em');
export const Code = el('code', 'Code');
export const H1 = el('h1', 'H1');
export const H2 = el('h2', 'H2');
export const H3 = el('h3', 'H3');
export const List = el('ul', 'List', { role: 'list' });
export const OList = el('ol', 'OList');
export const Item = el('li', 'Item');
export const Dl = el('dl', 'Dl');
export const Dt = el('dt', 'Dt');
export const Dd = el('dd', 'Dd');
export const Form = el('form', 'Form');
export const Header = el('header', 'Header');

export const ExtLink = forwardRef<HTMLAnchorElement, Omit<ComponentPropsWithoutRef<'a'>, 'target' | 'rel'>>(function ExtLink({ className, ...rest }, ref) {
  return <a {...rest} ref={ref} target="_blank" rel="noopener noreferrer" className={cn(className)} />;
});

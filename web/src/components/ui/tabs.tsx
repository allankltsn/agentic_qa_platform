import type { ReactNode } from 'react';
import { Tab, TabList, TabPanel, Tabs as AriaTabs } from 'react-aria-components';
import { cn } from '@/lib/utils';

export interface TabItem {
  id: string;
  label: string;
  count?: number;
  content: ReactNode;
}

export interface TabsProps {
  items: TabItem[];
  activeId: string;
  onChange: (id: string) => void;
  label: string;
  className?: string;
}

export function Tabs({ items, activeId, onChange, label, className }: TabsProps) {
  return (
    <AriaTabs selectedKey={activeId} onSelectionChange={(key) => onChange(String(key))} className={cn('flex flex-col', className)}>
      <TabList aria-label={label} className="flex gap-1 overflow-x-auto border-b border-line">
        {items.map((item) => (
          <Tab
            key={item.id}
            id={item.id}
            className={cn(
              'flex cursor-pointer items-center gap-2 whitespace-nowrap border-b-2 border-transparent px-4 py-3 text-button text-muted outline-none transition-colors',
              'data-[selected]:border-primary data-[selected]:text-ink hover:text-ink',
              'data-[focus-visible]:ring-2 data-[focus-visible]:ring-accent-text data-[focus-visible]:ring-offset-1',
            )}
          >
            {item.label}
            {item.count !== undefined ? <span className="rounded-full bg-surface-2 px-2 text-caption text-muted">{item.count}</span> : null}
          </Tab>
        ))}
      </TabList>
      {items.map((item) => (
        <TabPanel key={item.id} id={item.id} className="pt-5 outline-none data-[focus-visible]:ring-2 data-[focus-visible]:ring-accent-text">
          {item.content}
        </TabPanel>
      ))}
    </AriaTabs>
  );
}

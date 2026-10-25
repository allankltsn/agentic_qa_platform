import { forwardRef, type ReactNode } from 'react';
import {
  Button as AriaButton, Checkbox, CheckboxGroup, Input, Label, ListBox, ListBoxItem, Popover, Radio, RadioGroup,
  Select as AriaSelect, SelectValue, Text, TextArea, TextField as AriaTextField,
} from 'react-aria-components';
import { Icon, type IconName } from '@/brand';
import { cn } from '@/lib/utils';

const inputBase = [
  'w-full min-w-0 rounded-sm border border-line-strong bg-surface px-3 text-body text-ink placeholder:text-faint outline-none',
  'data-[focus-visible]:ring-2 data-[focus-visible]:ring-accent-text data-[focus]:border-primary data-[invalid]:border-danger',
  'data-[disabled]:cursor-not-allowed data-[disabled]:bg-surface-2 data-[disabled]:opacity-60',
];

const ErrorText = ({ error }: { error?: string }) =>
  error ? (
    <Text slot="errorMessage" role="alert" className="flex items-center gap-1 text-caption text-danger-text">
      <Icon name="warning" size={12} /><span>{error}</span>
    </Text>
  ) : null;

interface BaseProps {
  label: string;
  error?: string;
  hint?: string;
  className?: string;
}

export interface TextFieldProps extends BaseProps {
  value: string;
  onChange: (value: string) => void;
  onBlur?: () => void;
  placeholder?: string;
  maxLength?: number;
  autoFocus?: boolean;
  name?: string;
}

export const TextField = forwardRef<HTMLInputElement, TextFieldProps>(function TextField({ label, error, hint, className, placeholder, maxLength, ...rest }, ref) {
  return (
    <AriaTextField {...rest} isInvalid={Boolean(error)} validationBehavior="aria" className={cn('flex flex-col gap-1.5', className)}>
      <Label className="text-label text-ink">{label}</Label>
      <Input ref={ref} placeholder={placeholder} maxLength={maxLength} className={cn(inputBase, 'h-11')} />
      {hint ? <Text slot="description" className="text-caption text-muted">{hint}</Text> : null}
      <ErrorText error={error} />
    </AriaTextField>
  );
});

export const TextAreaField = forwardRef<HTMLTextAreaElement, TextFieldProps & { rows?: number }>(function TextAreaField({ label, error, hint, className, placeholder, maxLength, rows = 3, ...rest }, ref) {
  return (
    <AriaTextField {...rest} isInvalid={Boolean(error)} validationBehavior="aria" className={cn('flex flex-col gap-1.5', className)}>
      <Label className="text-label text-ink">{label}</Label>
      <TextArea ref={ref} placeholder={placeholder} maxLength={maxLength} rows={rows} className={cn(inputBase, 'resize-y py-2')} />
      {hint ? <Text slot="description" className="text-caption text-muted">{hint}</Text> : null}
      <ErrorText error={error} />
    </AriaTextField>
  );
});

export interface SelectOption { value: string; label: string }

export interface SelectFieldProps extends BaseProps {
  value: string;
  onChange: (value: string) => void;
  options: SelectOption[];
  /** Esconde o rótulo visualmente (continua acessível). */
  hideLabel?: boolean;
  size?: 'sm' | 'md';
}

export function SelectField({ label, hideLabel, error, hint, className, value, onChange, options, size = 'md' }: SelectFieldProps) {
  return (
    <AriaSelect
      aria-label={hideLabel ? label : undefined}
      selectedKey={value}
      onSelectionChange={(key) => onChange(String(key))}
      isInvalid={Boolean(error)}
      className={cn('flex flex-col gap-1.5', className)}
    >
      {hideLabel ? null : <Label className="text-label text-ink">{label}</Label>}
      <AriaButton
        className={cn(
          inputBase, 'flex items-center justify-between gap-2 text-left',
          'data-[pressed]:bg-surface-2 data-[focus-visible]:ring-2',
          size === 'sm' ? 'h-9 text-caption' : 'h-11',
        )}
      >
        <SelectValue className="truncate" />
        <svg aria-hidden="true" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="shrink-0 text-muted"><path d="m6 9 6 6 6-6" /></svg>
      </AriaButton>
      {hint ? <Text slot="description" className="text-caption text-muted">{hint}</Text> : null}
      <ErrorText error={error} />
      <Popover className="w-[--trigger-width] overflow-auto rounded-sm border border-line bg-surface shadow-dialog">
        <ListBox className="max-h-60 p-1 outline-none">
          {options.map((o) => (
            <ListBoxItem
              key={o.value}
              id={o.value}
              textValue={o.label}
              className="cursor-pointer rounded-sm px-3 py-2 text-body text-ink outline-none data-[focused]:bg-surface-2 data-[selected]:font-semibold data-[selected]:text-accent-text"
            >
              {o.label}
            </ListBoxItem>
          ))}
        </ListBox>
      </Popover>
    </AriaSelect>
  );
}

export interface ChoiceOption { value: string; label: string; description?: string; icon?: IconName }

const cardBase = [
  'flex cursor-pointer flex-col items-start gap-1 rounded-md border border-line-strong bg-surface p-3 text-left outline-none transition-colors',
  'data-[hovered]:bg-surface-2 data-[focus-visible]:ring-2 data-[focus-visible]:ring-accent-text',
  'data-[selected]:border-primary data-[selected]:bg-primary-soft',
];

const ChoiceContent = ({ o }: { o: ChoiceOption }) => (
  <>
    {o.icon ? <span className="text-accent-text"><Icon name={o.icon} size={20} /></span> : null}
    <span className="text-label">{o.label}</span>
    {o.description ? <span className="text-caption text-muted">{o.description}</span> : null}
  </>
);

/** Escolha única em cartões (ex.: tipo de projeto). */
export function RadioCards({ label, value, onChange, options, error }: { label: string; value: string; onChange: (v: string) => void; options: ChoiceOption[]; error?: string }) {
  return (
    <RadioGroup value={value} onChange={onChange} className="flex flex-col gap-1.5">
      <Label className="text-label text-ink">{label}</Label>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
        {options.map((o) => <Radio key={o.value} value={o.value} className={cn(cardBase)}><ChoiceContent o={o} /></Radio>)}
      </div>
      <ErrorText error={error} />
    </RadioGroup>
  );
}

/** Escolha múltipla em cartões (ex.: categorias de teste). */
export function CheckboxCards({ label, value, onChange, options, error }: { label: string; value: string[]; onChange: (v: string[]) => void; options: ChoiceOption[]; error?: string }) {
  return (
    <CheckboxGroup value={value} onChange={onChange} isInvalid={Boolean(error)} className="flex flex-col gap-1.5">
      <Label className="text-label text-ink">{label}</Label>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {options.map((o) => <Checkbox key={o.value} value={o.value} className={cn(cardBase)}><ChoiceContent o={o} /></Checkbox>)}
      </div>
      <ErrorText error={error} />
    </CheckboxGroup>
  );
}

export const FormRow = ({ children }: { children: ReactNode }) => <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">{children}</div>;

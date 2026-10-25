import type { ItemStatus, RunStatus, Severity, StepStatus } from './types';

export type Tone = 'neutral' | 'primary' | 'success' | 'warning' | 'danger' | 'info';

export const severityTone: Record<Severity, Tone> = { critical: 'danger', high: 'danger', medium: 'warning', low: 'info' };
export const itemStatusTone: Record<ItemStatus, Tone> = { pending: 'neutral', passed: 'success', failed: 'danger', skipped: 'neutral' };
export const runStatusTone: Record<RunStatus, Tone> = { running: 'info', completed: 'success', cancelled: 'neutral' };
export const RUN_STATUSES: Record<RunStatus, string> = { running: 'Em execução', completed: 'Concluída', cancelled: 'Interrompida' };
export const stepStatusTone: Record<StepStatus, Tone> = { pending: 'neutral', running: 'info', passed: 'success', failed: 'danger' };
export const STEP_STATUSES: Record<StepStatus, string> = { pending: 'Na fila', running: 'Executando', passed: 'OK', failed: 'Falhou' };

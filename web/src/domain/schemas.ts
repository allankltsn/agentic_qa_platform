import { z } from 'zod';
import { CATEGORY_IDS, SEVERITY_IDS, TYPE_IDS } from './catalog';

const optionalUrl = z.string().trim().max(300, 'Use até 300 caracteres');

export const projectSchema = z.object({
  name: z.string().trim().min(1, 'Informe o nome do projeto').max(80, 'Use até 80 caracteres'),
  type: z.enum(TYPE_IDS as [string, ...string[]]),
  categories: z.array(z.enum(CATEGORY_IDS as [string, ...string[]])).min(1, 'Escolha ao menos uma categoria'),
  description: z.string().trim().max(600, 'Use até 600 caracteres'),
  stack: z.string().trim().max(120, 'Use até 120 caracteres'),
  reference: optionalUrl,
});
export type ProjectInput = z.infer<typeof projectSchema>;

export const findingSchema = z.object({
  title: z.string().trim().min(1, 'Informe o título do achado').max(120, 'Use até 120 caracteres'),
  category: z.enum(CATEGORY_IDS as [string, ...string[]]),
  severity: z.enum(SEVERITY_IDS as [string, ...string[]]),
  status: z.enum(['open', 'in_progress', 'resolved']),
  itemId: z.string(),
  description: z.string().trim().min(1, 'Descreva o problema e o impacto').max(2000, 'Use até 2000 caracteres'),
  steps: z.string().trim().max(1500, 'Use até 1500 caracteres'),
  evidence: z.string().trim().max(1500, 'Use até 1500 caracteres'),
});
export type FindingInput = z.infer<typeof findingSchema>;

export const itemSchema = z.object({
  title: z.string().trim().min(1, 'Informe o que precisa ser validado').max(180, 'Use até 180 caracteres'),
  category: z.enum(CATEGORY_IDS as [string, ...string[]]),
});
export type ItemInput = z.infer<typeof itemSchema>;

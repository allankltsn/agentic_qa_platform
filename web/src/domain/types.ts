export type ProjectType = 'api' | 'frontend' | 'agent';
export type CategoryId = 'usability' | 'functionality' | 'vulnerabilities' | 'security';
export type Severity = 'critical' | 'high' | 'medium' | 'low';
export type ItemStatus = 'pending' | 'passed' | 'failed' | 'skipped';
export type FindingStatus = 'open' | 'in_progress' | 'resolved';

export interface ChecklistItem {
  id: string;
  category: CategoryId;
  title: string;
  status: ItemStatus;
  custom: boolean;
  /** Preenchido quando o resultado veio de uma execução de agente. */
  verifiedBy?: CategoryId;
}

export interface Finding {
  id: string;
  title: string;
  category: CategoryId;
  severity: Severity;
  status: FindingStatus;
  itemId: string;
  description: string;
  steps: string;
  evidence: string;
  createdAt: string;
  source: 'manual' | 'agent';
  runId?: string;
}

export type StepKind = 'act' | 'assert';
export type StepStatus = 'pending' | 'running' | 'passed' | 'failed';
export type RunStatus = 'running' | 'completed' | 'cancelled';
export type ProposalState = 'pending' | 'accepted' | 'dismissed';

export interface RunStep {
  id: string;
  kind: StepKind;
  text: string;
  itemId: string;
  status: StepStatus;
  /** Observação do agente depois de executar o passo. */
  note?: string;
}

export interface FindingProposal {
  id: string;
  itemId: string;
  title: string;
  severity: Severity;
  description: string;
  steps: string;
  evidence: string;
  state: ProposalState;
}

export interface Run {
  id: string;
  agent: CategoryId;
  status: RunStatus;
  startedAt: string;
  finishedAt?: string;
  steps: RunStep[];
  proposals: FindingProposal[];
}

export interface Project {
  id: string;
  name: string;
  type: ProjectType;
  categories: CategoryId[];
  description: string;
  stack: string;
  reference: string;
  createdAt: string;
  updatedAt: string;
  items: ChecklistItem[];
  findings: Finding[];
  runs: Run[];
}

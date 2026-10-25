import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { FindingInput, ItemInput, ProjectInput } from '@/domain/schemas';
import type { CategoryId, ItemStatus } from '@/domain/types';
import { api } from '@/mock/api';

export const keys = { projects: ['projects'] as const, project: (id: string) => ['projects', id] as const };

export const useProjects = () => useQuery({ queryKey: keys.projects, queryFn: api.listProjects });
export const useProject = (id: string | undefined) =>
  useQuery({ queryKey: keys.project(id ?? ''), queryFn: () => api.getProject(id as string), enabled: Boolean(id) });

/** Toda mutação revalida as consultas; o simulador de execuções também, via db.subscribe (ver providers). */
function useMutate<TArgs extends unknown[], TResult>(fn: (...args: TArgs) => Promise<TResult>) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (args: TArgs) => fn(...args),
    onSettled: () => client.invalidateQueries({ queryKey: keys.projects }),
  });
}

export const useCreateProject = () => {
  const m = useMutate((input: ProjectInput) => api.createProject(input));
  return { ...m, mutateAsync: (input: ProjectInput) => m.mutateAsync([input]) };
};
export const useUpdateProject = (id: string) => {
  const m = useMutate((input: ProjectInput) => api.updateProject(id, input));
  return { ...m, mutateAsync: (input: ProjectInput) => m.mutateAsync([input]) };
};
export const useDeleteProject = () => {
  const m = useMutate((id: string) => api.deleteProject(id));
  return { ...m, mutateAsync: (id: string) => m.mutateAsync([id]) };
};
export const useSetItemStatus = (projectId: string) => {
  const m = useMutate((itemId: string, status: ItemStatus) => api.setItemStatus(projectId, itemId, status));
  return { ...m, mutate: (itemId: string, status: ItemStatus) => m.mutate([itemId, status]) };
};
export const useAddItem = (projectId: string) => {
  const m = useMutate((input: ItemInput) => api.addItem(projectId, input));
  return { ...m, mutateAsync: (input: ItemInput) => m.mutateAsync([input]) };
};
export const useSaveFinding = (projectId: string) => {
  const m = useMutate((input: FindingInput, findingId?: string) => api.saveFinding(projectId, input, findingId));
  return { ...m, mutateAsync: (input: FindingInput, findingId?: string) => m.mutateAsync([input, findingId]) };
};
export const useDeleteFinding = (projectId: string) => {
  const m = useMutate((findingId: string) => api.deleteFinding(projectId, findingId));
  return { ...m, mutate: (findingId: string) => m.mutate([findingId]) };
};
export const useStartRun = (projectId: string) => {
  const m = useMutate((agent: CategoryId) => api.startRun(projectId, agent));
  return { ...m, mutate: (agent: CategoryId) => m.mutate([agent]) };
};
export const useCancelRun = (projectId: string) => {
  const m = useMutate((runId: string) => api.cancelRun(projectId, runId));
  return { ...m, mutate: (runId: string) => m.mutate([runId]) };
};
export const useResolveProposal = (projectId: string) => {
  const m = useMutate((runId: string, proposalId: string, decision: 'accepted' | 'dismissed') => api.resolveProposal(projectId, runId, proposalId, decision));
  return { ...m, mutate: (runId: string, proposalId: string, decision: 'accepted' | 'dismissed') => m.mutate([runId, proposalId, decision]) };
};

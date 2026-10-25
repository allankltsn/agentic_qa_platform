import { Box } from '@/components/ui/primitives';
import { Navigate, useOutletContext } from 'react-router';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/ui/empty-state';
import { Spinner } from '@/components/ui/spinner';
import { useProjects } from '@/hooks/queries';
import type { ShellContext } from '@/layouts/shell';

export function HomePage() {
  const { data, isLoading } = useProjects();
  const { newProject } = useOutletContext<ShellContext>();
  if (isLoading) return <Box className="grid place-items-center py-24"><Spinner size={28} label="Carregando" /></Box>;
  if (data?.length) return <Navigate to={`/app/projects/${data[0].id}`} replace />;
  return (
    <Box className="mx-auto max-w-2xl px-4 py-16">
      <EmptyState title="Nenhuma avaliação ainda" description="Crie a primeira avaliação para montar o checklist e a equipe de agentes especialistas." action={<Button leftIcon="plus" onClick={newProject}>Nova avaliação</Button>} />
    </Box>
  );
}

import { Box } from '@/components/ui/primitives';
import { Link } from 'react-router';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/ui/empty-state';

export function NotFoundPage() {
  return (
    <Box className="mx-auto max-w-2xl px-4 py-16">
      <EmptyState icon="warning" title="Página não encontrada" description="O endereço não existe ou a avaliação foi removida." action={<Button asChild><Link to="/app">Voltar ao workspace</Link></Button>} />
    </Box>
  );
}

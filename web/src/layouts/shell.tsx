import { useRef, useState } from 'react';
import { NavLink, Outlet, useMatch } from 'react-router';
import { Icon } from '@/brand';
import { Logo } from '@/brand';
import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/spinner';
import { useToast } from '@/components/ui/toast';
import { TYPES } from '@/domain/catalog';
import { useProjects } from '@/hooks/queries';
import { cn } from '@/lib/utils';
import { api } from '@/mock/api';
import { ProjectDialog } from '@/pages/project/ProjectDialog';
import { useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router';

export interface ShellContext { newProject: () => void }

export function Shell() {
  const { data: projects, isLoading } = useProjects();
  const { notify } = useToast();
  const client = useQueryClient();
  const navigate = useNavigate();
  const fileRef = useRef<HTMLInputElement>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const match = useMatch('/app/projects/:projectId');
  const current = projects?.find((p) => p.id === match?.params.projectId);

  const exportBackup = async () => {
    const text = await api.exportBackup();
    const url = URL.createObjectURL(new Blob([text], { type: 'application/json' }));
    const a = document.createElement('a');
    a.href = url;
    a.download = `prisma-qa-backup-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
    notify('Backup exportado.');
  };

  const importBackup = async (file: File | undefined) => {
    if (!file) return;
    try {
      const count = await api.importBackup(await file.text());
      await client.invalidateQueries();
      notify(`${count} avaliação(ões) importada(s).`);
      navigate('/app');
    } catch (e) {
      notify(e instanceof Error ? e.message : 'Não foi possível importar.', 'error');
    }
    if (fileRef.current) fileRef.current.value = '';
  };

  return (
    <div className="flex h-dvh w-full overflow-hidden">
      {menuOpen ? <div aria-hidden="true" className="fixed inset-0 z-20 bg-nav/50 md:hidden" onClick={() => setMenuOpen(false)} /> : null}
      <aside
        aria-label="Navegação de projetos"
        className={cn(
          'fixed inset-y-0 left-0 z-30 flex w-72 shrink-0 flex-col bg-nav px-4 pb-5 pt-7 text-nav-ink transition-transform duration-200 motion-reduce:transition-none md:relative md:translate-x-0',
          menuOpen ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <Logo className="px-2 text-nav-ink" />
        <div className="mb-3 mt-10 flex items-center justify-between px-2">
          <span className="text-kicker tracking-[0.16em] text-nav-muted">SEUS PROJETOS</span>
          <button type="button" aria-label="Criar avaliação" onClick={() => setCreating(true)} className="grid h-7 w-7 place-items-center rounded-sm bg-nav-2 text-accent outline-none hover:bg-nav-line focus-visible:ring-2 focus-visible:ring-accent">
            <Icon name="plus" size={16} />
          </button>
        </div>
        <nav aria-label="Projetos" className="flex-1 overflow-y-auto">
          {isLoading ? <div className="grid place-items-center py-6"><Spinner label="Carregando projetos" className="text-accent" /></div> : null}
          <ul className="flex flex-col gap-1">
            {projects?.map((p) => (
              <li key={p.id}>
                <NavLink
                  to={`/app/projects/${p.id}`}
                  onClick={() => setMenuOpen(false)}
                  className={({ isActive }) => cn(
                    'flex items-center gap-3 rounded-sm px-3 py-2.5 outline-none focus-visible:ring-2 focus-visible:ring-accent',
                    isActive ? 'bg-nav-2 text-nav-ink shadow-[inset_3px_0_0_rgb(var(--color-accent))]' : 'text-nav-muted hover:bg-nav-2/60 hover:text-nav-ink',
                  )}
                >
                  <span className="text-accent"><Icon name={TYPES[p.type].icon} size={18} /></span>
                  <span className="min-w-0">
                    <span className="block truncate text-label">{p.name}</span>
                    <span className="block text-caption text-nav-muted">{TYPES[p.type].label}</span>
                  </span>
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
        <div className="mt-4 flex flex-col gap-1">
          <div className="mb-3 flex gap-3 rounded-md border border-nav-line bg-nav-2/60 p-3">
            <span className="text-accent"><Icon name="shield" size={20} /></span>
            <div><strong className="text-label">Espaço privado</strong><p className="mt-1 text-caption text-nav-muted">Nesta fase os dados ficam neste navegador. Exporte um backup quando precisar.</p></div>
          </div>
          <Button variant="nav" size="sm" className="justify-start" leftIcon="upload" onClick={() => fileRef.current?.click()}>Importar backup</Button>
          <Button variant="nav" size="sm" className="justify-start" leftIcon="download" onClick={exportBackup}>Exportar backup</Button>
          <input ref={fileRef} type="file" accept="application/json,.json" hidden aria-label="Arquivo de backup" onChange={(e) => importBackup(e.target.files?.[0])} />
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <header className="flex min-h-16 shrink-0 items-center justify-between gap-3 border-b border-line bg-surface px-4 sm:px-8">
          <div className="flex min-w-0 items-center gap-3">
            <button type="button" aria-label="Abrir menu" onClick={() => setMenuOpen(true)} className="grid h-10 w-10 place-items-center rounded-sm text-ink outline-none hover:bg-surface-2 focus-visible:ring-2 focus-visible:ring-accent-text md:hidden">
              <Icon name="menu" />
            </button>
            <div className="truncate text-kicker uppercase tracking-[0.14em] text-muted">WORKSPACE <span className="px-1">/</span> <strong className="text-ink">{current?.name ?? 'Avaliações'}</strong></div>
          </div>
          <div className="flex items-center gap-3">
            <span className="hidden items-center gap-2 text-caption text-muted sm:flex"><span className="h-2 w-2 rounded-full bg-success" />Salvo neste navegador</span>
            <Button leftIcon="plus" onClick={() => setCreating(true)}>Nova avaliação</Button>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto">
          <Outlet context={{ newProject: () => setCreating(true) } satisfies ShellContext} />
        </main>
      </div>

      <ProjectDialog isOpen={creating} onOpenChange={setCreating} onSaved={(p) => navigate(`/app/projects/${p.id}`)} />
    </div>
  );
}

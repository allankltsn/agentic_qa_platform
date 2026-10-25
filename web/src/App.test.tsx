import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { beforeEach, describe, expect, it } from 'vitest';
import { App } from './App';
import { mockLatency } from './mock/api';
import { db } from './mock/db';
import { runnerConfig } from './mock/runner';
import { Providers } from './providers';

beforeEach(() => {
  localStorage.clear();
  db.reset();
  mockLatency.ms = 0;
  runnerConfig.stepDelayMs = 0;
});

const setup = () => render(<Providers router={false}><MemoryRouter initialEntries={['/app']}><App /></MemoryRouter></Providers>);

describe('App', () => {
  it('abre o projeto de exemplo com indicadores e abas', async () => {
    setup();
    expect(await screen.findByRole('heading', { level: 1, name: /API de autenticação/ })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Visão geral/ })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByText('Progresso do checklist')).toBeInTheDocument();
  });

  it('cria uma avaliação, validando o nome', async () => {
    const user = userEvent.setup();
    setup();
    await screen.findByRole('heading', { level: 1, name: /API de autenticação/ });
    await user.click(screen.getAllByRole('button', { name: /Nova avaliação/ })[0]);
    const dialog = await screen.findByRole('dialog');
    await user.click(within(dialog).getByRole('button', { name: 'Salvar avaliação' }));
    expect(await within(dialog).findByText('Informe o nome do projeto')).toBeInTheDocument();
    await user.type(within(dialog).getByRole('textbox', { name: 'Nome do projeto' }), 'Portal do cliente');
    await user.click(within(dialog).getByRole('button', { name: 'Salvar avaliação' }));
    expect(await screen.findByRole('heading', { level: 1, name: 'Portal do cliente' })).toBeInTheDocument();
  });

  it('executa um agente e mostra a execução concluída', async () => {
    const user = userEvent.setup();
    setup();
    await screen.findByRole('heading', { level: 1, name: /API de autenticação/ });
    await user.click(screen.getByRole('tab', { name: /Agentes/ }));
    await user.click(await screen.findByRole('button', { name: 'Executar Sol · Segurança' }));
    await waitFor(() => expect(screen.getAllByText('Concluída').length).toBeGreaterThan(0), { timeout: 5000 });
    expect(screen.getByRole('list', { name: 'Passos da execução' })).toBeInTheDocument();
  });
});

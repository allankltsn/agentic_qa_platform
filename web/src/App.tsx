import { lazy, Suspense } from 'react';
import { Navigate, Route, Routes } from 'react-router';
import { Spinner } from './components/ui/spinner';
import { Shell } from './layouts/shell';

// Páginas sob demanda: o chunk inicial fica com React, roteador e casca; cada tela baixa o que usa ao ser visitada.
const HomePage = lazy(() => import('./pages/HomePage').then((m) => ({ default: m.HomePage })));
const ProjectPage = lazy(() => import('./pages/project/ProjectPage').then((m) => ({ default: m.ProjectPage })));
const NotFoundPage = lazy(() => import('./pages/NotFoundPage').then((m) => ({ default: m.NotFoundPage })));

export function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/app" replace />} />
      <Route path="/app" element={<Shell />}>
        <Route index element={<Suspense fallback={<Spinner size={28} className="m-auto mt-24" />}><HomePage /></Suspense>} />
        <Route path="projects/:projectId" element={<Suspense fallback={<Spinner size={28} className="m-auto mt-24" />}><ProjectPage /></Suspense>} />
        <Route path="*" element={<Suspense fallback={null}><NotFoundPage /></Suspense>} />
      </Route>
      <Route path="*" element={<Navigate to="/app" replace />} />
    </Routes>
  );
}

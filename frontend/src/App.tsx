import { useEffect, useState } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import { ErrorBoundary } from 'react-error-boundary';
import { Layout } from './components/layout';
import { LoginPage } from './components/LoginPage';
import { setAccessTokenGetter } from './api/client';
import { CommodityPage } from './pages/commodity';
import { AIChatPage } from './pages/chat';
import { DashboardPage } from './pages/dashboard';
import { MetricsPage } from './pages/metrics';
import { ProfilePage } from './pages/profile';
import { SettingsPage } from './pages/settings';
import { TrainPage } from './pages/train';
import { AboutPage } from './pages/about';
import { Logo } from './components/Logo';
import { motion } from 'framer-motion';

const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: 'commodity/:name', element: <CommodityPage /> },
      { path: 'chat', element: <AIChatPage /> },
      { path: 'train', element: <TrainPage /> },
      { path: 'metrics', element: <MetricsPage /> },
      { path: 'profile', element: <ProfilePage /> },
      { path: 'settings', element: <SettingsPage /> },
      { path: 'about', element: <AboutPage /> },
    ],
  },
]);

export default function App() {
  const { isAuthenticated, isLoading, getAccessTokenSilently, getIdTokenClaims } = useAuth0();
  const audience = import.meta.env.VITE_AUTH0_AUDIENCE;
  const [authReady, setAuthReady] = useState(false);

  useEffect(() => {
    setAuthReady(false);
    setAccessTokenGetter(async () => {
      if (!isAuthenticated) return undefined;
      try {
        const claims = await getIdTokenClaims().catch(() => undefined);
        if (claims?.__raw) return claims.__raw;
      } catch {
        // Fall through to access token fallback below.
      }

      return getAccessTokenSilently({
        authorizationParams: audience ? { audience } : undefined,
      }).catch(() => undefined);
    });
    setAuthReady(true);
  }, [audience, getAccessTokenSilently, getIdTokenClaims, isAuthenticated]);

  const LoadingScreen = ({ message }: { message: string }) => (
    <div className="flex min-h-screen flex-col items-center justify-center bg-[var(--bg)]" style={{ background: 'linear-gradient(145deg, var(--bg), var(--bg-accent))' }}>
      <motion.div
        animate={{ scale: [0.95, 1.05, 0.95], opacity: [0.7, 1, 0.7] }}
        transition={{ repeat: Infinity, duration: 2, ease: 'easeInOut' }}
        className="relative flex items-center justify-center rounded-2xl p-6 shadow-[var(--shadow)]"
        style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
      >
        <Logo size={48} />
      </motion.div>
      <motion.p
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="mt-6 text-sm font-medium tracking-wide"
        style={{ color: 'var(--text-muted)' }}
      >
        {message}
      </motion.p>
    </div>
  );

  if (isLoading) {
    return <LoadingScreen message="Authenticating session..." />;
  }

  if (!isAuthenticated) {
    return <LoginPage />;
  }

  if (!authReady) {
    return <LoadingScreen message="Securing connection..." />;
  }

  return (
    <ErrorBoundary fallback={<div className="p-4">Something went wrong.</div>}>
      <RouterProvider router={router} />
    </ErrorBoundary>
  );
}

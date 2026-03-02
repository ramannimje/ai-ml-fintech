import { useEffect, useState } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import { ErrorBoundary } from 'react-error-boundary';
import { Layout } from './components/layout';
import { LoginPage } from './components/LoginPage';
import { setAccessTokenGetter } from './api/client';
import { CommodityPage } from './pages/commodity';
import { DashboardPage } from './pages/dashboard';
import { MetricsPage } from './pages/metrics';
import { TrainPage } from './pages/train';

const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: 'commodity/:name', element: <CommodityPage /> },
      { path: 'train', element: <TrainPage /> },
      { path: 'metrics', element: <MetricsPage /> },
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

  if (isLoading) {
    return <div className="flex min-h-screen items-center justify-center text-sm">Loading authentication...</div>;
  }

  if (!isAuthenticated) {
    return <LoginPage />;
  }

  if (!authReady) {
    return <div className="flex min-h-screen items-center justify-center text-sm">Preparing secure session...</div>;
  }

  return (
    <ErrorBoundary fallback={<div className="p-4">Something went wrong.</div>}>
      <RouterProvider router={router} />
    </ErrorBoundary>
  );
}

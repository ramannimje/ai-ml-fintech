import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import { ErrorBoundary } from 'react-error-boundary';
import { Layout } from './components/layout';
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
  return (
    <ErrorBoundary fallback={<div className="p-4">Something went wrong.</div>}>
      <RouterProvider router={router} />
    </ErrorBoundary>
  );
}

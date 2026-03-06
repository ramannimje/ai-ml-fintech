import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClientProvider } from '@tanstack/react-query';
import { Auth0Provider } from '@auth0/auth0-react';
import App from './App';
import { queryClient } from './lib/query';
import { ThemeSync } from './components/theme-sync';
import { resolveAuthCallbackUrl } from './lib/auth';
import './index.css';

const authDomain = import.meta.env.VITE_AUTH0_DOMAIN || __AUTH0_DOMAIN__ || '';
const authClientId = import.meta.env.VITE_AUTH0_CLIENT_ID || __AUTH0_CLIENT_ID__ || '';
const authAudience = import.meta.env.VITE_AUTH0_AUDIENCE || __AUTH0_AUDIENCE__;
const authCallbackUrl = resolveAuthCallbackUrl(import.meta.env.VITE_AUTH0_CALLBACK_URL);
const hasPlaceholderAuth0 = authDomain.includes('your-tenant.auth0.com') || authClientId.includes('your-client-id');
const isAuthConfigured = !!authDomain && !!authClientId && !hasPlaceholderAuth0;

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    {isAuthConfigured ? (
      <Auth0Provider
        domain={authDomain}
        clientId={authClientId}
        authorizationParams={{
          redirect_uri: authCallbackUrl,
          ...(authAudience ? { audience: authAudience } : {}),
        }}
        cacheLocation="memory"
        onRedirectCallback={() => {
          window.history.replaceState({}, document.title, '/');
        }}
      >
        <QueryClientProvider client={queryClient}>
          <ThemeSync />
          <App />
        </QueryClientProvider>
      </Auth0Provider>
    ) : (
      <div style={{ padding: '1rem', fontFamily: 'system-ui' }}>
        Missing Auth0 config. Set <code>VITE_AUTH0_DOMAIN</code> and <code>VITE_AUTH0_CLIENT_ID</code>.
      </div>
    )}
  </React.StrictMode>,
);

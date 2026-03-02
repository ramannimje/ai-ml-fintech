import { useAuth0 } from '@auth0/auth0-react';
import { Chrome, Facebook } from 'lucide-react';

function MicrosoftIcon() {
  return (
    <span className="inline-grid h-4 w-4 grid-cols-2 gap-[1px] rounded-sm bg-black p-[1px]">
      <span className="bg-[#f25022]" />
      <span className="bg-[#7fba00]" />
      <span className="bg-[#00a4ef]" />
      <span className="bg-[#ffb900]" />
    </span>
  );
}

export function LoginPage() {
  const { loginWithRedirect } = useAuth0();
  const redirectUri = import.meta.env.VITE_AUTH0_CALLBACK_URL || window.location.origin;

  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-10">
      <div className="surface-card w-full max-w-md rounded-2xl p-6 shadow-sm">
        <h1 className="text-2xl font-semibold">Sign In</h1>
        <p className="text-muted mt-2 text-sm">Continue with your preferred identity provider.</p>
        <div className="mt-6 space-y-3">
          <button
            type="button"
            onClick={() =>
              loginWithRedirect({
                authorizationParams: {
                  connection: 'google-oauth2',
                  redirect_uri: redirectUri,
                },
              })
            }
            className="ui-input flex w-full items-center justify-center gap-2 rounded-lg bg-white px-4 py-2 font-medium text-black hover:opacity-90"
          >
            <Chrome className="h-4 w-4" />
            Continue with Google
          </button>
          <button
            type="button"
            onClick={() =>
              loginWithRedirect({
                authorizationParams: {
                  connection: 'facebook',
                  redirect_uri: redirectUri,
                },
              })
            }
            className="flex w-full items-center justify-center gap-2 rounded-lg border border-blue-700 bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700"
          >
            <Facebook className="h-4 w-4" />
            Continue with Facebook
          </button>
          <button
            type="button"
            onClick={() =>
              loginWithRedirect({
                authorizationParams: {
                  connection: 'windowslive',
                  redirect_uri: redirectUri,
                },
              })
            }
            className="flex w-full items-center justify-center gap-2 rounded-lg border border-slate-900 bg-slate-800 px-4 py-2 font-medium text-white hover:bg-slate-900"
          >
            <MicrosoftIcon />
            Continue with Microsoft
          </button>
        </div>
      </div>
    </div>
  );
}

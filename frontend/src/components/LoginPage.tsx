import { useMemo } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import { useQuery } from '@tanstack/react-query';
import { client } from '../api/client';

export function LoginPage() {
  const { loginWithRedirect } = useAuth0();
  const redirectUri = import.meta.env.VITE_AUTH0_CALLBACK_URL || window.location.origin;

  const liveTeaser = useQuery({
    queryKey: ['public-live-prices-india'],
    queryFn: () => client.publicLivePricesByRegion('india'),
    refetchInterval: 60_000,
    staleTime: 45_000,
  });

  const teaser = useMemo(() => {
    const list = liveTeaser.data ?? [];
    const gold = list.find((item) => item.commodity === 'gold');
    const silver = list.find((item) => item.commodity === 'silver');
    const crude = list.find((item) => item.commodity === 'crude_oil');
    return [gold, silver, crude];
  }, [liveTeaser.data]);

  const connect = (connection: 'google-oauth2' | 'facebook' | 'windowslive') => {
    loginWithRedirect({
      authorizationParams: {
        connection,
        redirect_uri: redirectUri,
      },
    });
  };

  return (
    <div className="min-h-screen px-4 py-10" style={{ background: 'linear-gradient(145deg, #040b18, #0a1731)' }}>
      <div className="mx-auto grid min-h-[88vh] max-w-6xl items-center gap-6 lg:grid-cols-[1.1fr,0.9fr]">
        <section className="panel rounded-2xl p-8 md:p-10" style={{ background: 'linear-gradient(145deg, rgba(8,26,54,0.96), rgba(13,42,87,0.95))', borderColor: 'rgba(215,184,108,0.28)' }}>
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-accent">Aureus Wealth Desk</p>
          <h1 className="mt-4 text-4xl font-semibold leading-tight text-white sm:text-5xl">A private commodity intelligence platform for disciplined capital decisions.</h1>
          <p className="mt-4 max-w-xl text-sm leading-relaxed" style={{ color: '#d5e0f4' }}>
            Access live bullion and energy feeds, AI scenario forecasts, and risk alerts in one institutional-grade workspace.
          </p>
          <div className="mt-8 grid grid-cols-1 gap-3 sm:grid-cols-3">
            {teaser.map((item, idx) => (
              <article key={idx} className="rounded-xl border px-4 py-3" style={{ borderColor: 'rgba(215,184,108,0.28)', background: 'rgba(6, 17, 36, 0.48)' }}>
                <p className="text-xs uppercase tracking-[0.12em]" style={{ color: '#aebfdd' }}>{item?.commodity?.replace('_', ' ') || 'Loading'}</p>
                <p className="mt-1 text-xl font-semibold text-white">{item ? `${item.live_price.toFixed(2)} ${item.currency}` : '...'}</p>
                <p className="text-xs text-accent">{item?.unit || 'Live market feed'}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="panel rounded-2xl p-8" style={{ background: 'rgba(9, 24, 48, 0.94)', borderColor: 'rgba(214,182,104,0.25)' }}>
          <h2 className="text-3xl font-semibold text-white">Sign In</h2>
          <p className="mt-2 text-sm" style={{ color: '#c5d4ef' }}>Use your approved identity provider to access portfolio intelligence.</p>
          <div className="mt-6 space-y-3">
            <button type="button" onClick={() => connect('google-oauth2')} className="btn-primary w-full">
              Continue with Google
            </button>
            <button type="button" onClick={() => connect('facebook')} className="btn-primary w-full">
              Continue with Facebook
            </button>
            <button type="button" onClick={() => connect('windowslive')} className="btn-primary w-full">
              Continue with Microsoft
            </button>
          </div>
        </section>
      </div>
    </div>
  );
}

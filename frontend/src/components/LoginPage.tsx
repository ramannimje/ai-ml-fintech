import { useEffect, useMemo, useRef } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import { useQuery } from '@tanstack/react-query';
import { Chrome, Facebook } from 'lucide-react';
import { client } from '../api/client';

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

function MarketBackground() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let frame = 0;
    let raf = 0;

    const draw = () => {
      const width = canvas.clientWidth;
      const height = canvas.clientHeight;
      canvas.width = width;
      canvas.height = height;

      ctx.clearRect(0, 0, width, height);
      ctx.fillStyle = '#07111d';
      ctx.fillRect(0, 0, width, height);

      const lines = [
        { color: 'rgba(208, 164, 58, 0.68)', amplitude: 24, speed: 0.015 },
        { color: 'rgba(118, 159, 219, 0.62)', amplitude: 18, speed: 0.02 },
        { color: 'rgba(87, 132, 208, 0.68)', amplitude: 22, speed: 0.012 },
      ];

      for (const line of lines) {
        ctx.beginPath();
        ctx.strokeStyle = line.color;
        ctx.lineWidth = 2;
        for (let x = 0; x < width; x += 4) {
          const y = height * 0.3 + Math.sin((x + frame * 10) * line.speed) * line.amplitude + (x / width) * 140;
          if (x === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();
      }

      for (let i = 0; i < 48; i += 1) {
        const x = (i * 27 + frame * 5) % width;
        const open = height * 0.62 + Math.sin((i + frame) * 0.2) * 40;
        const close = open + Math.sin((i + frame) * 0.4) * 14;
        const high = Math.min(open, close) - 10;
        const low = Math.max(open, close) + 10;
        const bullish = close < open;
        ctx.strokeStyle = bullish ? 'rgba(202, 161, 63, 0.8)' : 'rgba(112, 158, 228, 0.8)';
        ctx.fillStyle = ctx.strokeStyle;
        ctx.beginPath();
        ctx.moveTo(x, high);
        ctx.lineTo(x, low);
        ctx.stroke();
        ctx.fillRect(x - 3, Math.min(open, close), 6, Math.abs(close - open) + 2);
      }

      frame += 1;
      raf = requestAnimationFrame(draw);
    };

    raf = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(raf);
  }, []);

  return (
    <>
      <canvas ref={canvasRef} className="absolute inset-0 h-full w-full opacity-80" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_15%_20%,rgba(255,255,255,0.16),transparent_45%),radial-gradient(circle_at_80%_10%,rgba(212,175,88,0.12),transparent_42%),linear-gradient(120deg,rgba(8,22,49,0.84),rgba(13,35,74,0.9))]" />
      <div className="pointer-events-none absolute inset-0 finance-grid opacity-30" />
      <div className="pointer-events-none absolute inset-0 finance-particles" />
    </>
  );
}

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
    return { gold, silver, crude };
  }, [liveTeaser.data]);

  return (
    <div className="relative min-h-screen overflow-hidden px-4 py-10">
      <MarketBackground />
      <div className="relative z-10 mx-auto flex min-h-[90vh] max-w-6xl flex-col justify-center gap-8 lg:flex-row lg:items-center lg:justify-between">
        <div className="max-w-xl text-white">
          <p className="text-xs uppercase tracking-[0.28em] text-amber-200">AI Commodity Terminal</p>
          <h1 className="mt-3 text-4xl font-semibold leading-tight sm:text-5xl">Track Gold. Predict Moves. Trade with conviction.</h1>
          <p className="mt-4 max-w-lg text-sm text-slate-200 sm:text-base">
            Live commodity streams are running now. Sign in to unlock AI forecasts, personalized alerts, and intraday market intelligence.
          </p>
          <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-3">
            {[teaser.gold, teaser.silver, teaser.crude].map((item, idx) => (
              <div key={idx} className="rounded-xl border border-blue-200/30 bg-blue-950/35 px-4 py-3 backdrop-blur-md">
                <div className="text-xs uppercase text-blue-100">{item?.commodity?.replace('_', ' ') || 'Loading'}</div>
                <div className="mt-1 text-lg font-medium">
                  {item ? `${item.live_price.toFixed(2)} ${item.currency}` : '...'}
                </div>
                <div className="text-xs text-amber-200">{item?.unit || 'Live market feed'}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="w-full max-w-md rounded-2xl border border-blue-200/30 bg-blue-950/40 p-6 text-white shadow-2xl backdrop-blur-2xl">
          <h2 className="text-2xl font-semibold">Sign In</h2>
          <p className="mt-2 text-sm text-slate-100">Continue with your preferred identity provider.</p>
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
              className="flex w-full items-center justify-center gap-2 rounded-lg border border-amber-300 bg-amber-300 px-4 py-2 font-medium text-blue-950 hover:bg-amber-200"
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
              className="flex w-full items-center justify-center gap-2 rounded-lg border border-blue-400 bg-blue-700 px-4 py-2 font-medium text-white hover:bg-blue-600"
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
              className="flex w-full items-center justify-center gap-2 rounded-lg border border-blue-300 bg-blue-900 px-4 py-2 font-medium text-white hover:bg-blue-800"
            >
              <MicrosoftIcon />
              Continue with Microsoft
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

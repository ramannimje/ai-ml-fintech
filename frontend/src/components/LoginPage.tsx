import { useMemo } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import { useQuery } from '@tanstack/react-query';
import { client } from '../api/client';
import { resolveAuthCallbackUrl } from '../lib/auth';
import { TrendingUp, TrendingDown, Shield, Zap, BarChart3 } from 'lucide-react';

export function LoginPage() {
  const { loginWithRedirect } = useAuth0();
  const redirectUri = resolveAuthCallbackUrl(import.meta.env.VITE_AUTH0_CALLBACK_URL);

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
    <div className="login-page">
      {/* Background with gradient and grid pattern */}
      <div className="login-background" />
      
      <div className="login-container">
        {/* Left Column - Value Proposition (60%) */}
        <section className="login-left">
          {/* Logo */}
          <div className="login-logo">
            <span className="logo-text">TRADESIGHT</span>
          </div>

          {/* Headline */}
          <div className="login-content">
            <h1 className="login-headline">
              A private commodity intelligence platform for disciplined capital decisions.
            </h1>
            <p className="login-subheadline">
              Access live bullion and energy feeds, AI scenario forecasts, and risk alerts in one institutional-grade workspace.
            </p>

            {/* Feature Pills */}
            <div className="feature-pills">
              <div className="feature-pill">
                <Shield size={18} />
                <span>Institutional Grade</span>
              </div>
              <div className="feature-pill">
                <Zap size={18} />
                <span>Live Feeds</span>
              </div>
              <div className="feature-pill">
                <BarChart3 size={18} />
                <span>AI Forecasts</span>
              </div>
            </div>

            {/* Bento Box Commodity Cards */}
            <div className="bento-box">
              {teaser.map((item, idx) => {
                const isPositive = item?.daily_change_pct && item.daily_change_pct >= 0;
                return (
                  <div key={idx} className="commodity-card">
                    <div className="card-header">
                      <span className="card-name">{item?.commodity?.replace('_', ' ') || 'Loading'}</span>
                      <span className={`card-change ${isPositive ? 'positive' : 'negative'}`}>
                        {isPositive ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                        {item?.daily_change_pct?.toFixed(2) || '0.00'}%
                      </span>
                    </div>
                    <div className="card-price">
                      {item ? `${item.live_price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '...'}
                      <span className="card-currency">{item?.currency || ''}</span>
                    </div>
                    <div className="card-unit">{item?.unit || 'Live market feed'}</div>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        {/* Right Column - Sign In Form (40%) */}
        <section className="login-right">
          <div className="signin-panel">
            <h2 className="signin-title">Sign In</h2>
            <p className="signin-subtitle">Use your approved identity provider to access portfolio intelligence.</p>
            
            <div className="signin-buttons">
              <button type="button" onClick={() => connect('google-oauth2')} className="auth-button">
                <svg className="auth-icon" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                </svg>
                Continue with Google
              </button>
              
              <button type="button" onClick={() => connect('facebook')} className="auth-button">
                <svg className="auth-icon" viewBox="0 0 24 24" fill="#1877F2">
                  <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
                </svg>
                Continue with Facebook
              </button>
              
              <button type="button" onClick={() => connect('windowslive')} className="auth-button">
                <svg className="auth-icon" viewBox="0 0 24 24" fill="#00A4EF">
                  <path d="M11.4 24H0V12.6h11.4V24zM24 24H12.6V12.6H24V24zM11.4 11.4H0V0h11.4v11.4zm12.6 0H12.6V0H24v11.4z"/>
                </svg>
                Continue with Microsoft
              </button>
            </div>

            <p className="signin-footer">
              Secure access powered by Auth0
            </p>
          </div>
        </section>
      </div>

      {/* Inline Styles */}
      <style>{`
        /* Background with radial gradient and grid pattern */
        .login-page {
          position: relative;
          min-height: 100vh;
          overflow: hidden;
        }

        .login-background {
          position: absolute;
          inset: 0;
          background: radial-gradient(circle at center, #0F172A 0%, #020617 100%);
        }

        .login-background::before {
          content: '';
          position: absolute;
          inset: 0;
          background-image: 
            linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px);
          background-size: 40px 40px;
          opacity: 0.05;
          pointer-events: none;
        }

        /* Container */
        .login-container {
          position: relative;
          z-index: 1;
          display: grid;
          grid-template-columns: 1.1fr 0.9fr;
          gap: 2rem;
          max-width: 1400px;
          margin: 0 auto;
          padding: 2rem;
          min-height: 100vh;
          align-items: center;
        }

        @media (max-width: 1024px) {
          .login-container {
            grid-template-columns: 1fr;
            padding: 1.5rem;
          }
        }

        /* Left Column */
        .login-left {
          display: flex;
          flex-direction: column;
          gap: 3rem;
        }

        /* Logo */
        .login-logo {
          margin-bottom: 1rem;
        }

        .logo-text {
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          font-size: 1rem;
          font-weight: 700;
          color: #d4af37;
          letter-spacing: 0.2em;
          text-transform: uppercase;
        }

        /* Content */
        .login-content {
          display: flex;
          flex-direction: column;
          gap: 2rem;
        }

        /* Headline - Premium Serif */
        .login-headline {
          font-family: 'Playfair Display', 'Lora', Georgia, serif;
          font-size: 2.75rem;
          font-weight: 600;
          line-height: 1.2;
          color: #ffffff;
          max-width: 680px;
        }

        @media (max-width: 768px) {
          .login-headline {
            font-size: 2rem;
          }
        }

        /* Subheadline */
        .login-subheadline {
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          font-size: 1rem;
          line-height: 1.6;
          color: #94a3b8;
          max-width: 580px;
        }

        /* Feature Pills */
        .feature-pills {
          display: flex;
          gap: 1rem;
          flex-wrap: wrap;
        }

        .feature-pill {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.5rem 1rem;
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 999px;
          color: #94a3b8;
          font-size: 0.875rem;
          font-weight: 500;
        }

        /* Bento Box */
        .bento-box {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 1rem;
          margin-top: 1rem;
        }

        @media (max-width: 768px) {
          .bento-box {
            grid-template-columns: 1fr;
          }
        }

        /* Commodity Cards */
        .commodity-card {
          background: rgba(255, 255, 255, 0.03);
          backdrop-filter: blur(12px);
          -webkit-backdrop-filter: blur(12px);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 16px;
          padding: 1.25rem;
          transition: all 200ms ease;
        }

        .commodity-card:hover {
          background: rgba(255, 255, 255, 0.05);
          border-color: rgba(212, 175, 55, 0.3);
          transform: translateY(-2px);
        }

        .card-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 0.75rem;
        }

        .card-name {
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          font-size: 0.75rem;
          font-weight: 600;
          color: #94a3b8;
          text-transform: uppercase;
          letter-spacing: 0.08em;
        }

        .card-change {
          display: flex;
          align-items: center;
          gap: 0.25rem;
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          font-size: 0.75rem;
          font-weight: 600;
          animation: pulse 2s ease-in-out infinite;
        }

        .card-change.positive {
          color: #10b981;
        }

        .card-change.negative {
          color: #ef4444;
        }

        @keyframes pulse {
          0%, 100% {
            opacity: 1;
          }
          50% {
            opacity: 0.7;
          }
        }

        .card-price {
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          font-size: 1.5rem;
          font-weight: 700;
          color: #ffffff;
          font-variant-numeric: tabular-nums;
          margin-bottom: 0.25rem;
        }

        .card-currency {
          font-size: 0.875rem;
          font-weight: 600;
          color: #64748b;
          margin-left: 0.375rem;
        }

        .card-unit {
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          font-size: 0.7rem;
          color: #475569;
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }

        /* Right Column */
        .login-right {
          display: flex;
          align-items: center;
          justify-content: center;
        }

        /* Sign In Panel */
        .signin-panel {
          width: 100%;
          max-width: 420px;
          background: rgba(255, 255, 255, 0.02);
          backdrop-filter: blur(20px);
          -webkit-backdrop-filter: blur(20px);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 24px;
          padding: 2.5rem;
        }

        @media (max-width: 768px) {
          .signin-panel {
            padding: 2rem;
          }
        }

        .signin-title {
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          font-size: 1.75rem;
          font-weight: 700;
          color: #ffffff;
          margin-bottom: 0.5rem;
        }

        .signin-subtitle {
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          font-size: 0.875rem;
          color: #64748b;
          line-height: 1.5;
        }

        /* Auth Buttons */
        .signin-buttons {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
          margin-top: 2rem;
        }

        .auth-button {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.75rem;
          width: 100%;
          height: 48px;
          background: #1E293B;
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 12px;
          color: #ffffff;
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          font-size: 0.875rem;
          font-weight: 500;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          cursor: pointer;
          transition: all 200ms ease;
        }

        .auth-button:hover {
          background: #1E293B;
          border-color: #d4af37;
          transform: scale(1.05);
        }

        .auth-icon {
          width: 20px;
          height: 20px;
        }

        .signin-footer {
          margin-top: 1.5rem;
          text-align: center;
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          font-size: 0.75rem;
          color: #475569;
        }

        /* Responsive adjustments */
        @media (max-width: 1024px) {
          .login-left {
            gap: 2rem;
          }

          .login-headline {
            font-size: 2.25rem;
          }
        }

        @media (max-width: 768px) {
          .login-logo {
            text-align: center;
          }

          .login-content {
            align-items: center;
            text-align: center;
          }

          .feature-pills {
            justify-content: center;
          }
        }
      `}</style>
    </div>
  );
}

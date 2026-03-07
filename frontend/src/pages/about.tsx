import { motion } from 'framer-motion';
import { Linkedin, ExternalLink, BarChart3, Globe, Bell, MessageSquare, Brain, Shield } from 'lucide-react';
import ramanPhoto from '../assets/Raman-Photo.jpg';
import chanchalPhoto from '../assets/Chanchal-Photo.png';

const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.12, duration: 0.5, ease: 'easeOut' },
  }),
};

const features = [
  { icon: Globe, title: 'Multi-Region Pricing', desc: 'Real-time bullion & energy feeds across India, US, and Europe with regional currency and unit context.' },
  { icon: Brain, title: 'AI Scenario Forecasting', desc: 'Ensemble ML models (XGBoost, Prophet, Chronos) deliver point forecasts with confidence intervals and bull/bear scenarios.' },
  { icon: Bell, title: 'Smart Alerts', desc: 'Configurable price threshold alerts via email and WhatsApp with full history tracking and CSV export.' },
  { icon: MessageSquare, title: 'Advisory AI Chat', desc: 'Gemini-powered market advisory that synthesizes live data, technical indicators, and macro context.' },
  { icon: BarChart3, title: 'Model Studio', desc: 'Train, benchmark, and compare models per commodity and region with walk-forward validation metrics.' },
  { icon: Shield, title: 'Institutional-Grade Security', desc: 'Auth0 authentication, Infisical secret management, and end-to-end encrypted data pipelines.' },
];

const builders = [
  {
    name: 'Raman Nimje',
    title: 'Vice President of AI Software Engineering',
    org: 'Goldman Sachs',
    role: 'Full-stack engineering, ML pipeline, and platform architecture',
    linkedin: 'https://www.linkedin.com/in/raman-fullstack/',
    photo: ramanPhoto,
  },
  {
    name: 'Chanchal Nikhare',
    title: 'Senior Product Designer',
    org: 'Intone Networks',
    role: 'Product design, UX strategy, and visual identity',
    linkedin: 'https://www.linkedin.com/in/chanchalnikhare/',
    photo: chanchalPhoto,
  },
];

export function AboutPage() {
  return (
    <div className="space-y-10">
      {/* Hero */}
      <motion.section
        id="about-hero"
        initial="hidden"
        animate="visible"
        variants={fadeUp}
        custom={0}
      >
        <p className="kpi-label text-accent">About TradeSight</p>
        <h1 className="shell-title mt-3">Intelligence that moves with the market.</h1>
        <p className="shell-subtitle mt-3">
          TradeSight is an AI-powered, multi-region commodity market intelligence platform built for disciplined capital decisions.
          It delivers real-time pricing, scenario forecasting, and advisory insights for gold, silver, and crude oil — across India, US, and Europe — in one institutional-grade workspace.
        </p>
      </motion.section>

      {/* Features */}
      <motion.section id="about-features" initial="hidden" animate="visible">
        <h2 className="text-2xl font-semibold" style={{ color: 'var(--text)' }}>
          Platform Capabilities
        </h2>
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((f, i) => (
            <motion.article
              key={f.title}
              id={`about-feature-${i}`}
              className="panel panel-hover-gold p-5"
              variants={fadeUp}
              custom={i + 1}
            >
              <div
                className="flex h-10 w-10 items-center justify-center rounded-xl"
                style={{ background: 'color-mix(in srgb, var(--gold) 15%, transparent)' }}
              >
                <f.icon size={20} className="text-accent" />
              </div>
              <h3 className="mt-3 text-base font-semibold" style={{ color: 'var(--text)' }}>
                {f.title}
              </h3>
              <p className="mt-1.5 text-sm leading-relaxed" style={{ color: 'var(--text-muted)' }}>
                {f.desc}
              </p>
            </motion.article>
          ))}
        </div>
      </motion.section>

      {/* Builders */}
      <motion.section id="about-builders" initial="hidden" animate="visible">
        <h2 className="text-2xl font-semibold" style={{ color: 'var(--text)' }}>
          Meet the Builders
        </h2>
        <p className="mt-2 text-sm" style={{ color: 'var(--text-muted)' }}>
          Built by engineers and designers who understand both markets and modern software.
        </p>
        <div className="mt-6 grid gap-5 sm:grid-cols-2">
          {builders.map((b, i) => (
            <motion.article
              key={b.name}
              id={`about-builder-${i}`}
              className="panel panel-hover-gold overflow-hidden"
              variants={fadeUp}
              custom={i + 4}
            >
              <div
                className="h-1.5 w-full"
                style={{ background: 'linear-gradient(90deg, var(--gold), var(--gold-soft), transparent)' }}
              />
              <div className="p-6">
                <div className="flex items-start gap-4">
                  <div className="h-16 w-16 shrink-0 overflow-hidden rounded-full border-2" style={{ borderColor: 'var(--border-strong)' }}>
                    <img
                      src={b.photo}
                      alt={`${b.name} profile`}
                      className="h-full w-full object-cover"
                    />
                  </div>
                  <div className="min-w-0 pt-0.5">
                    <h3 className="text-lg font-semibold" style={{ color: 'var(--text)' }}>
                      {b.name}
                    </h3>
                    <p className="text-sm font-medium text-accent">{b.title}</p>
                    <p className="text-xs" style={{ color: 'var(--text-muted)' }}>{b.org}</p>
                  </div>
                </div>
                <p className="mt-4 text-sm leading-relaxed" style={{ color: 'var(--text-muted)' }}>
                  <span className="font-semibold" style={{ color: 'var(--text)' }}>Role in TradeSight:</span>{' '}
                  {b.role}
                </p>
                <a
                  id={`about-linkedin-${i}`}
                  href={b.linkedin}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-primary mt-4 inline-flex items-center gap-2"
                >
                  <Linkedin size={16} />
                  View LinkedIn Profile
                  <ExternalLink size={14} />
                </a>
              </div>
            </motion.article>
          ))}
        </div>
      </motion.section>

      {/* Mission */}
      <motion.section
        id="about-mission"
        className="panel p-6 md:p-8"
        style={{ borderColor: 'color-mix(in srgb, var(--gold) 25%, var(--border))' }}
        variants={fadeUp}
        initial="hidden"
        animate="visible"
        custom={7}
      >
        <h2 className="text-2xl font-semibold" style={{ color: 'var(--text)' }}>
          Our Mission
        </h2>
        <p className="mt-3 text-sm leading-relaxed" style={{ color: 'var(--text-muted)' }}>
          We believe commodity intelligence should be accessible, transparent, and powered by the best of modern AI. TradeSight
          was built to give traders, analysts, and investors the same caliber of tooling that institutional desks rely on — without
          the complexity or cost. Every forecast, alert, and insight is designed to support confident, data-driven capital decisions.
        </p>
      </motion.section>
    </div>
  );
}

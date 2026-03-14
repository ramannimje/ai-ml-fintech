/**
 * TradeSight Design Tokens
 * Institutional-grade design system for market intelligence
 */

export const tokens = {
  // Spacing scale (pixels)
  spacing: [0, 4, 8, 12, 16, 24, 32, 48, 64, 96, 128],

  // Border radius
  radii: {
    none: '0',
    sm: '8px',
    md: '12px',
    lg: '16px',
    xl: '24px',
    '2xl': '32px',
    full: '9999px',
  },

  // Font families
  fonts: {
    heading: '"Cormorant Garamond", "Times New Roman", serif',
    body: '"Manrope", "Segoe UI", sans-serif',
    mono: '"JetBrains Mono", "Fira Code", monospace',
  },

  // Font sizes (rem)
  fontSizes: {
    xs: '0.75rem',     // 12px
    sm: '0.875rem',    // 14px
    base: '1rem',      // 16px
    lg: '1.125rem',    // 18px
    xl: '1.25rem',     // 20px
    '2xl': '1.5rem',   // 24px
    '3xl': '1.875rem', // 30px
    '4xl': '2.25rem',  // 36px
    '5xl': '3rem',     // 48px
  },

  // Font weights
  fontWeights: {
    normal: '400',
    medium: '500',
    semibold: '600',
    bold: '700',
    extrabold: '800',
  },

  // Letter spacing
  letterSpacings: {
    tight: '-0.02em',
    normal: '0',
    wide: '0.02em',
    wider: '0.05em',
    widest: '0.1em',
    ultra: '0.2em',
  },

  // Line heights
  lineHeights: {
    none: '1',
    tight: '1.25',
    snug: '1.375',
    normal: '1.5',
    relaxed: '1.625',
    loose: '2',
  },

  // Breakpoints (Tailwind default)
  breakpoints: {
    sm: '640px',
    md: '768px',
    lg: '1024px',
    xl: '1280px',
    '2xl': '1536px',
  },

  // Shadows (using CSS variables)
  shadows: {
    sm: 'var(--shadow)',
    md: '0 4px 12px rgba(0, 0, 0, 0.08)',
    lg: '0 10px 24px rgba(0, 0, 0, 0.12)',
    xl: '0 20px 40px rgba(0, 0, 0, 0.16)',
    inner: 'inset 0 2px 4px rgba(0, 0, 0, 0.06)',
  },

  // Transitions
  transitions: {
    fast: '150ms ease',
    normal: '200ms ease',
    slow: '300ms ease',
    spring: 'cubic-bezier(0.175, 0.885, 0.32, 1.275)',
  },

  // Z-index scale
  zIndex: {
    hide: -1,
    auto: 'auto',
    base: 0,
    dropdown: 1000,
    sticky: 1100,
    overlay: 1200,
    modal: 1300,
    popover: 1400,
    toast: 1500,
    tooltip: 1600,
  },
} as const;

// Color palettes by semantic role
export const colors = {
  // Semantic colors
  background: {
    primary: 'var(--bg)',
    secondary: 'var(--bg-accent)',
    surface: 'var(--surface)',
    surface2: 'var(--surface-2)',
  },
  text: {
    primary: 'var(--text)',
    secondary: 'var(--text-muted)',
    inverse: '#ffffff',
    gold: 'var(--gold)',
  },
  border: {
    default: 'var(--border)',
    strong: 'var(--border-strong)',
  },
  status: {
    success: 'var(--success)',
    danger: 'var(--danger)',
    warning: '#d29d3f',
    info: 'var(--primary-soft)',
  },
  accent: {
    gold: 'var(--gold)',
    goldSoft: 'var(--gold-soft)',
    primary: 'var(--primary)',
    primarySoft: 'var(--primary-soft)',
  },
} as const;

// Component-specific tokens
export const componentTokens = {
  button: {
    heights: {
      sm: '36px',
      md: '44px',
      lg: '52px',
    },
    fontSizes: {
      sm: '0.7rem',
      md: '0.78rem',
      lg: '0.9rem',
    },
  },
  input: {
    heights: {
      sm: '36px',
      md: '44px',
      lg: '52px',
    },
  },
  card: {
    padding: {
      sm: '1rem',
      md: '1.5rem',
      lg: '2rem',
    },
  },
  badge: {
    fontSizes: {
      sm: '0.6rem',
      md: '0.7rem',
      lg: '0.8rem',
    },
  },
} as const;

export type TokenCategory = keyof typeof tokens;
export type ColorCategory = keyof typeof colors;

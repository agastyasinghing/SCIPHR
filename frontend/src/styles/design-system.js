/**
 * SCIPHR Design System
 * Inspired by FightSignal but elevated with our own style
 */

export const colors = {
  // Base colors
  background: {
    primary: '#0A0E14',      // Deep dark blue-black
    secondary: '#0F1419',    // Slightly lighter
    tertiary: '#1A1F2E',     // Card backgrounds
    elevated: '#222938',     // Elevated cards/modals
  },
  
  // Fighter colors (for vs matchups)
  fighter: {
    red: {
      gradient: ['#FF4655', '#C9184A', '#590D22'],  // Red fighter gradient
      glow: 'rgba(255, 70, 85, 0.3)',
      solid: '#FF4655',
    },
    blue: {
      gradient: ['#4F46E5', '#7C3AED', '#2D1B69'],  // Purple/blue fighter gradient
      glow: 'rgba(79, 70, 229, 0.3)',
      solid: '#4F46E5',
    },
  },
  
  // Accent colors
  accent: {
    yellow: '#FACC15',       // Primary CTA (like FightSignal)
    yellowGlow: 'rgba(250, 204, 21, 0.3)',
    cyan: '#06B6D4',         // Secondary actions
    cyanGlow: 'rgba(6, 182, 212, 0.3)',
    lime: '#84CC16',         // Success/positive
    orange: '#F97316',       // Warning/hot
    red: '#EF4444',          // Danger/negative
  },
  
  // Value indicators (NEW - our edge over FightSignal)
  value: {
    high: '#84CC16',         // High value bet
    medium: '#FACC15',       // Medium value
    low: '#94A3B8',          // Low value
    negative: '#64748B',     // No value
  },
  
  // Text colors
  text: {
    primary: '#F8FAFC',      // Main text
    secondary: '#CBD5E1',    // Secondary text
    tertiary: '#94A3B8',     // Muted text
    muted: '#64748B',        // Very muted
  },
  
  // Border colors
  border: {
    primary: 'rgba(255, 255, 255, 0.1)',
    secondary: 'rgba(255, 255, 255, 0.05)',
    focus: '#4F46E5',
  },
  
  // Status colors
  status: {
    live: '#EF4444',         // Live indicator
    upcoming: '#FACC15',
    past: '#64748B',
  },
  
  // Confidence levels
  confidence: {
    high: '#84CC16',
    medium: '#FACC15',
    low: '#EF4444',
  },
};

export const typography = {
  fonts: {
    primary: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    mono: "'JetBrains Mono', 'Fira Code', monospace",
  },
  
  sizes: {
    xs: '0.75rem',      // 12px
    sm: '0.875rem',     // 14px
    base: '1rem',       // 16px
    lg: '1.125rem',     // 18px
    xl: '1.25rem',      // 20px
    '2xl': '1.5rem',    // 24px
    '3xl': '1.875rem',  // 30px
    '4xl': '2.25rem',   // 36px
    '5xl': '3rem',      // 48px
    '6xl': '3.75rem',   // 60px
  },
  
  weights: {
    normal: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
    extrabold: 800,
  },
  
  lineHeights: {
    tight: 1.2,
    normal: 1.5,
    relaxed: 1.75,
  },
};

export const spacing = {
  xs: '0.25rem',   // 4px
  sm: '0.5rem',    // 8px
  md: '1rem',      // 16px
  lg: '1.5rem',    // 24px
  xl: '2rem',      // 32px
  '2xl': '3rem',   // 48px
  '3xl': '4rem',   // 64px
  '4xl': '6rem',   // 96px
};

export const borderRadius = {
  sm: '0.25rem',   // 4px
  md: '0.5rem',    // 8px
  lg: '0.75rem',   // 12px
  xl: '1rem',      // 16px
  '2xl': '1.5rem', // 24px
  full: '9999px',
};

export const shadows = {
  sm: '0 1px 2px 0 rgba(0, 0, 0, 0.3)',
  md: '0 4px 6px -1px rgba(0, 0, 0, 0.4)',
  lg: '0 10px 15px -3px rgba(0, 0, 0, 0.5)',
  xl: '0 20px 25px -5px rgba(0, 0, 0, 0.6)',
  glow: {
    yellow: '0 0 20px rgba(250, 204, 21, 0.3)',
    cyan: '0 0 20px rgba(6, 182, 212, 0.3)',
    red: '0 0 20px rgba(255, 70, 85, 0.3)',
    blue: '0 0 20px rgba(79, 70, 229, 0.3)',
  },
};

export const animations = {
  duration: {
    fast: '150ms',
    normal: '300ms',
    slow: '500ms',
  },
  
  easing: {
    default: 'cubic-bezier(0.4, 0, 0.2, 1)',
    in: 'cubic-bezier(0.4, 0, 1, 1)',
    out: 'cubic-bezier(0, 0, 0.2, 1)',
    inOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
  },
};

export const breakpoints = {
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px',
};

// Utility function to create gradients
export const gradients = {
  fighterRed: `linear-gradient(135deg, ${colors.fighter.red.gradient.join(', ')})`,
  fighterBlue: `linear-gradient(135deg, ${colors.fighter.blue.gradient.join(', ')})`,
  heroBg: `linear-gradient(135deg, #1A1F2E 0%, #0F1419 100%)`,
  cardGlass: 'linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.02) 100%)',
};

// Utility function to create glassmorphism effect
export const glassmorphism = {
  light: {
    background: 'rgba(255, 255, 255, 0.05)',
    backdropFilter: 'blur(10px)',
    border: '1px solid rgba(255, 255, 255, 0.1)',
  },
  medium: {
    background: 'rgba(255, 255, 255, 0.08)',
    backdropFilter: 'blur(15px)',
    border: '1px solid rgba(255, 255, 255, 0.15)',
  },
  dark: {
    background: 'rgba(0, 0, 0, 0.3)',
    backdropFilter: 'blur(20px)',
    border: '1px solid rgba(255, 255, 255, 0.1)',
  },
};

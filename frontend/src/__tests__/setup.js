import '@testing-library/jest-dom';
import { vi } from 'vitest';

globalThis.IntersectionObserver = vi.fn(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));

// html2canvas is not available in jsdom — mock it globally
vi.mock('html2canvas', () => ({ default: vi.fn().mockResolvedValue({ toDataURL: () => '' }) }));

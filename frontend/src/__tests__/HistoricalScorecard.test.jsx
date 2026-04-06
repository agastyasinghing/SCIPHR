import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { vi } from 'vitest';
import HistoricalScorecard from '../pages/HistoricalScorecard';

vi.mock('../api/api', () => ({
  default: {
    getHistoricalScorecard: vi.fn(),
  },
}));

import api from '../api/api';

const wrapper = ({ children }) => <BrowserRouter>{children}</BrowserRouter>;

describe('HistoricalScorecard — empty state', () => {
  beforeEach(() => vi.clearAllMocks());

  it('shows empty state when predictions array is empty', async () => {
    api.getHistoricalScorecard.mockResolvedValueOnce({
      predictions: [], total: 0, accuracy: null, resolved_count: 0, limit: 50, offset: 0,
    });

    render(<HistoricalScorecard />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText(/No prediction history yet/i)).toBeTruthy();
    });
  });

  it('fetches scorecard on mount', async () => {
    api.getHistoricalScorecard.mockResolvedValueOnce({ predictions: [], total: 0 });
    render(<HistoricalScorecard />, { wrapper });
    await waitFor(() => expect(api.getHistoricalScorecard).toHaveBeenCalledTimes(1));
  });

  it('renders prediction rows when data exists', async () => {
    api.getHistoricalScorecard.mockResolvedValueOnce({
      predictions: [
        { id: 1, fighter1: 'Jon Jones', fighter2: 'Stipe Miocic', predicted_winner: 'Jon Jones', confidence: 0.72, actual_winner: 'Jon Jones', correct: true, value_signal: 'EDGE_DETECTED', edge_pct: 0.08, created_at: '2026-04-01T10:00:00Z' },
      ],
      total: 1,
      accuracy: 100.0,
      resolved_count: 1,
    });

    render(<HistoricalScorecard />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText(/Jon Jones vs Stipe Miocic/i)).toBeTruthy();
      expect(screen.getByText('Correct')).toBeTruthy();
    });
  });

  it('shows error state on fetch failure', async () => {
    api.getHistoricalScorecard.mockRejectedValueOnce(new Error('500'));
    render(<HistoricalScorecard />, { wrapper });
    await waitFor(() => expect(document.querySelector('.scorecard-error')).toBeTruthy());
  });
});

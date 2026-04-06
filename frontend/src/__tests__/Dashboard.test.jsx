import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { vi } from 'vitest';
import Dashboard from '../pages/Dashboard';

vi.mock('../api/api', () => ({
  default: {
    getUpcomingEvents: vi.fn(),
    getPastEvents: vi.fn(),
  },
}));

import api from '../api/api';

const wrapper = ({ children }) => <BrowserRouter>{children}</BrowserRouter>;

const mockUpcoming = {
  events: [
    { id: 1, name: 'UFC 400', date: '2026-05-01', location: 'Las Vegas', fights: [{ r_fighter: 'Jon Jones', b_fighter: 'Stipe Miocic' }] },
  ],
};
const mockPast = { events: [] };

describe('Dashboard — events data fetching', () => {
  beforeEach(() => vi.clearAllMocks());

  it('fetches events on mount', async () => {
    api.getUpcomingEvents.mockResolvedValueOnce(mockUpcoming);
    api.getPastEvents.mockResolvedValueOnce(mockPast);

    render(<Dashboard />, { wrapper });

    await waitFor(() => {
      expect(api.getUpcomingEvents).toHaveBeenCalledTimes(1);
      expect(api.getPastEvents).toHaveBeenCalledTimes(1);
    });
  });

  it('shows error banner when fetch fails', async () => {
    api.getUpcomingEvents.mockRejectedValueOnce(new Error('503 Service Unavailable'));
    api.getPastEvents.mockRejectedValueOnce(new Error('503 Service Unavailable'));

    render(<Dashboard />, { wrapper });

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeTruthy();
    });
  });

  it('passes event data to HeroFightCard', async () => {
    api.getUpcomingEvents.mockResolvedValueOnce(mockUpcoming);
    api.getPastEvents.mockResolvedValueOnce(mockPast);

    render(<Dashboard />, { wrapper });

    await waitFor(() => {
      // HeroFightCard renders the event name from the real event data
      expect(screen.getAllByText('UFC 400').length).toBeGreaterThan(0);
    });
  });

  it('shows loading state before events resolve', async () => {
    // Promise that never resolves — keeps dashboard in loading state
    api.getUpcomingEvents.mockReturnValueOnce(new Promise(() => {}));
    api.getPastEvents.mockReturnValueOnce(new Promise(() => {}));

    render(<Dashboard />, { wrapper });

    expect(screen.getByLabelText('Loading events')).toBeTruthy();
  });

  it('transitions from loading to populated state', async () => {
    api.getUpcomingEvents.mockResolvedValueOnce(mockUpcoming);
    api.getPastEvents.mockResolvedValueOnce(mockPast);

    render(<Dashboard />, { wrapper });

    // Loading spinner visible immediately
    expect(screen.getByLabelText('Loading events')).toBeTruthy();

    // After data loads, HeroFightCard renders with real event
    await waitFor(() => {
      expect(screen.queryByLabelText('Loading events')).toBeNull();
      expect(screen.getAllByText('UFC 400').length).toBeGreaterThan(0);
    });
  });
});

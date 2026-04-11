import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { vi } from 'vitest';
import FighterSearch from '../pages/FighterSearch';

vi.mock('../api/api', () => ({
  default: {
    getFighters: vi.fn(),
  },
}));

import api from '../api/api';

const wrapper = ({ children }) => <BrowserRouter>{children}</BrowserRouter>;

describe('FighterSearch', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders fighter cards when API returns data', async () => {
    api.getFighters.mockResolvedValueOnce({
      fighters: [
        { name: 'Jon Jones', weight_class: 'Heavyweight', is_active: true },
        { name: 'Islam Makhachev', weight_class: 'Lightweight', is_active: true },
      ],
      count: 2,
    });

    render(<FighterSearch />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Jon Jones')).toBeTruthy();
      expect(screen.getByText('Islam Makhachev')).toBeTruthy();
    });
  });

  it('shows error card when API call fails — not silent 0 fighters', async () => {
    api.getFighters.mockRejectedValueOnce(new Error('422 Unprocessable Entity'));

    render(<FighterSearch />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Could not load fighters')).toBeTruthy();
    });

    // Must NOT silently show 0 fighters with no explanation
    expect(screen.queryByText(/0 Fighters/i)).toBeNull();
  });

  it('requests limit=5000 to cover full fighter database', async () => {
    api.getFighters.mockResolvedValueOnce({ fighters: [], count: 0 });

    render(<FighterSearch />, { wrapper });

    await waitFor(() => {
      expect(api.getFighters).toHaveBeenCalledWith('', 5000);
    });
  });
});

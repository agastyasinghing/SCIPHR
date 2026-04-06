import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';
import FightPoster from '../components/picks/FightPoster';

vi.mock('../api/api', () => ({ default: { request: vi.fn() } }));
vi.mock('../utils/imageUtils', () => ({ getFighterImage: () => '/placeholder.png' }));

const mockFighter1 = { name: 'Jon Jones',  stats: { wins_total: 27, losses_total: 1, draw: 0, weight_class: 'Heavyweight' } };
const mockFighter2 = { name: 'Stipe Miocic', stats: { wins_total: 20, losses_total: 4, draw: 0, weight_class: 'Heavyweight' } };

const mockPrediction = {
  winner: 'Jon Jones',
  confidence: 0.72,
  intelligence: {
    cinematic_title: { title: 'Crown or Collapse', subtitle: 'Heavyweight · CHAOS HIGH', weight_class_color: '#7C3AED' },
    badges: [
      { key: 'FRAUD_CHECK', label: 'Fraud Check', color: 'amber', reason: 'Overrated by market.', fighter: 'Stipe Miocic' },
      { key: 'DOG_WITH_TEETH', label: 'Dog With Teeth', color: 'orange', reason: 'Model sees upset edge.', fighter: 'Stipe Miocic' },
    ],
  },
};

describe('FightPoster — cinematic title', () => {
  it('shows FIGHT NIGHT when no prediction', () => {
    render(<FightPoster fighter1={mockFighter1} fighter2={mockFighter2} prediction={null} loading={false} onSelectFighter={() => {}} onGeneratePrediction={() => {}} />);
    expect(screen.getByText('FIGHT NIGHT')).toBeTruthy();
  });

  it('replaces FIGHT NIGHT with cinematic title after prediction', () => {
    render(<FightPoster fighter1={mockFighter1} fighter2={mockFighter2} prediction={mockPrediction} loading={false} onSelectFighter={() => {}} onGeneratePrediction={() => {}} />);
    expect(screen.getByText('Crown or Collapse')).toBeTruthy();
    expect(screen.queryByText('FIGHT NIGHT')).toBeNull();
  });

  it('shows cinematic subtitle', () => {
    render(<FightPoster fighter1={mockFighter1} fighter2={mockFighter2} prediction={mockPrediction} loading={false} onSelectFighter={() => {}} onGeneratePrediction={() => {}} />);
    expect(screen.getByText('Heavyweight · CHAOS HIGH')).toBeTruthy();
  });
});

describe('FightPoster — badges', () => {
  it('renders badges when present', () => {
    render(<FightPoster fighter1={mockFighter1} fighter2={mockFighter2} prediction={mockPrediction} loading={false} onSelectFighter={() => {}} onGeneratePrediction={() => {}} />);
    expect(screen.getByText('Fraud Check')).toBeTruthy();
    expect(screen.getByText('Dog With Teeth')).toBeTruthy();
  });

  it('renders no badge strip when badges array is empty', () => {
    const pred = { ...mockPrediction, intelligence: { ...mockPrediction.intelligence, badges: [] } };
    render(<FightPoster fighter1={mockFighter1} fighter2={mockFighter2} prediction={pred} loading={false} onSelectFighter={() => {}} onGeneratePrediction={() => {}} />);
    expect(document.querySelector('.poster-badges')).toBeNull();
  });

  it('renders no badge strip when intelligence is null', () => {
    const pred = { ...mockPrediction, intelligence: null };
    render(<FightPoster fighter1={mockFighter1} fighter2={mockFighter2} prediction={pred} loading={false} onSelectFighter={() => {}} onGeneratePrediction={() => {}} />);
    expect(document.querySelector('.poster-badges')).toBeNull();
  });
});

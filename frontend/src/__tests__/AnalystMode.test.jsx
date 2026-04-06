import { render, screen, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';
import AnalystMode from '../components/picks/AnalystMode';

const mockRequest = vi.fn();
vi.mock('../api/api', () => ({ default: { request: mockRequest } }));

const f1 = { name: 'Islam Makhachev', stats: {} };
const f2 = { name: 'Charles Oliveira', stats: {} };

const fullIntel = {
  cinematic_title: { title: 'Ground War', subtitle: 'Lightweight', weight_class_color: '#10B981' },
  badges: [{ key: 'CHAOS_CERTIFIED', label: 'Chaos Certified', color: 'yellow', reason: 'High chaos.', fighter: 'Charles Oliveira' }],
  chaos: { available: true, score: 74, tier: 'HIGH', drivers: ['style_clash'], betting_implication: 'Avoid heavy chalk.', confidence: 0.8 },
  perception_gap: { available: true, gap_f1: 0.12, gap_f2: -0.12, label: 'STRONG', overvalued_fighter: 'Islam Makhachev', undervalued_fighter: 'Charles Oliveira', aura_score_f1: 0.8, aura_score_f2: 0.6, direction_f1: 'OVERHYPED', direction_f2: 'UNDERRATED', magnitude: 'MODERATE' },
  narrative_trap: { available: true, risk: 'HIGH', active_traps: ['HYPE_TRAIN'], trapped_fighter: 'Islam Makhachev' },
  false_consensus: { available: true, is_coinflip: true, consensus_fighter: 'Islam Makhachev', actual_gap: 0.06, label: 'INVISIBLE_COINFLIP', display_message: 'Public sees chalk. Model sees coin.' },
  nightmare: { available: true, is_nightmare: true, nightmare_fighter: 'Islam Makhachev', style_f1: 'GRAPPLER', style_f2: 'SUBMISSION', matchup_label: 'GRAPPLER_VS_SUBMISSION', severity: 'SEVERE' },
  win_path: { available: true, f1_paths: [{ path: 'DECISION_VOLUME', probability: 0.45 }], f2_paths: [{ path: 'SUBMISSION', probability: 0.55 }], most_likely_method: 'SUB', f1_primary_threat: 'GRAPPLING', f2_primary_threat: 'SUBMISSION' },
  fight_dna: { available: true, f1_dna: { striking: 0.7, grappling: 0.9 }, f2_dna: { striking: 0.5, grappling: 0.95 }, collision_type: 'GRAPPLER_VS_SUBMISSION', style_clash_intensity: 0.6, primary_dimension: 'grappling' },
  value_bet: { signal: 'EDGE_DETECTED', active: true, edge_pct: 0.082, kelly_fraction: 0.04, model_prob_f1: 0.51, implied_prob_f1: 0.43, model_prob_f2: 0.49, implied_prob_f2: 0.57 },
  upset_alert: { is_alert: true, underdog_name: 'Charles Oliveira', model_probability: 0.49, implied_probability: 0.43, edge: 0.06, american_odds: 140, payout_multiplier: 2.4, reason: 'UNDERDOG_EDGE' },
  sharp_money: { aligned: true, movement_magnitude: 0.07, signal: 'MARKET_ALIGNMENT' },
};

const mockPrediction = {
  winner: 'Islam Makhachev',
  confidence: 0.55,
  fighter1_stats: { wins_total: 24, losses_total: 1, draw: 0, str_acc: 55, str_def: 62 },
  fighter2_stats: { wins_total: 33, losses_total: 9, draw: 0, str_acc: 50, str_def: 58 },
  intelligence: fullIntel,
};

describe('AnalystMode — no secondary API call', () => {
  it('does not call /detailed-stats', () => {
    mockRequest.mockClear();
    render(<AnalystMode fighter1={f1} fighter2={f2} prediction={mockPrediction} />);
    expect(mockRequest).not.toHaveBeenCalled();
  });
});

describe('AnalystMode — Intelligence tab', () => {
  beforeEach(() => {
    render(<AnalystMode fighter1={f1} fighter2={f2} prediction={mockPrediction} />);
    fireEvent.click(screen.getByText('Intelligence'));
  });

  it('renders cinematic title', () => {
    expect(screen.getAllByText('Ground War').length).toBeGreaterThan(0);
  });

  it('renders badges', () => {
    expect(screen.getByText('Chaos Certified')).toBeTruthy();
  });

  it('renders chaos score', () => {
    expect(screen.getByText(/74\/100/)).toBeTruthy();
  });

  it('renders kill chain paths', () => {
    expect(screen.getByText('Kill Chain')).toBeTruthy();
  });

  it('renders value bet signal', () => {
    expect(screen.getByText(/EDGE DETECTED/i)).toBeTruthy();
  });
});

describe('AnalystMode — null intelligence modules do not crash', () => {
  it('renders Intelligence tab with all modules null', () => {
    const pred = { ...mockPrediction, intelligence: { badges: [], cinematic_title: null, chaos: null, perception_gap: null, narrative_trap: null, false_consensus: null, nightmare: null, win_path: null, fight_dna: null, value_bet: null, upset_alert: null, sharp_money: null } };
    render(<AnalystMode fighter1={f1} fighter2={f2} prediction={pred} />);
    fireEvent.click(screen.getByText('Intelligence'));
    expect(screen.getByText(/Run a prediction/i)).toBeTruthy();
  });

  it('renders with null prediction prop', () => {
    render(<AnalystMode fighter1={f1} fighter2={f2} prediction={null} />);
    expect(document.querySelector('.analyst-mode')).toBeTruthy();
  });
});

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../api/api';
import Card from '../components/shared/Card';
import Button from '../components/shared/Button';
import './FighterProfile.css';
import { getFighterImage } from '../utils/imageUtils';

/**
 * Fighter Profile Page
 * Display full fighter stats and information
 */
const FighterProfile = () => {
  const { name } = useParams();
  const navigate = useNavigate();
  const [fighter, setFighter] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Weight class colors
  const weightClassColors = {
    'Strawweight': { primary: '#EC4899', secondary: '#BE185D', bg: 'rgba(236, 72, 153, 0.1)' },
    'Flyweight': { primary: '#8B5CF6', secondary: '#6D28D9', bg: 'rgba(139, 92, 246, 0.1)' },
    'Bantamweight': { primary: '#3B82F6', secondary: '#1D4ED8', bg: 'rgba(59, 130, 246, 0.1)' },
    'Featherweight': { primary: '#06B6D4', secondary: '#0E7490', bg: 'rgba(6, 182, 212, 0.1)' },
    'Lightweight': { primary: '#10B981', secondary: '#047857', bg: 'rgba(16, 185, 129, 0.1)' },
    'Welterweight': { primary: '#FACC15', secondary: '#CA8A04', bg: 'rgba(250, 204, 21, 0.1)' },
    'Middleweight': { primary: '#F59E0B', secondary: '#D97706', bg: 'rgba(245, 158, 11, 0.1)' },
    'Light Heavyweight': { primary: '#EF4444', secondary: '#B91C1C', bg: 'rgba(239, 68, 68, 0.1)' },
    'Heavyweight': { primary: '#7C3AED', secondary: '#5B21B6', bg: 'rgba(124, 58, 237, 0.1)' },
  };
  
  useEffect(() => {
    loadFighterProfile();
  }, [name]);
  
  const loadFighterProfile = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.getFighterProfile(name);
      setFighter(result);
    } catch (err) {
      console.error('Failed to load fighter:', err);
      setError('Fighter not found');
    } finally {
      setLoading(false);
    }
  };
  
  if (loading) {
    return (
      <div className="fighter-profile-page">
        <div className="container">
          <div className="loading-state">
            <div className="loading-spinner"></div>
            <p>Loading fighter profile...</p>
          </div>
        </div>
      </div>
    );
  }
  
  if (error || !fighter) {
    return (
      <div className="fighter-profile-page">
        <div className="container">
          <div className="error-state">
            <span className="error-icon">❌</span>
            <h2>Fighter Not Found</h2>
            <p>We couldn't find a fighter with that name.</p>
            <Button onClick={() => navigate('/fighters')}>
              Back to Fighters
            </Button>
          </div>
        </div>
      </div>
    );
  }
  
  const stats = fighter.stats;
  const weightClass = stats.weight_class || 'Unknown';
  const colors = weightClassColors[weightClass] || weightClassColors['Welterweight'];
  
  // Format stats
  const wins = Math.round(stats.wins_total || 0);
  const losses = Math.round(stats.losses_total || 0);
  const draws = Math.round(stats.draw || 0);
  const age = Math.round(stats.age || 0);
  const height = stats.height ? `${Math.round(stats.height)} cm` : 'N/A';
  const reach = stats.reach ? `${Math.round(stats.reach)} cm` : 'N/A';
  const weight = stats.weight ? `${Math.round(stats.weight)} lbs` : 'N/A';
  
  // Striking stats
  const slpm = (stats.SLpM_total || 0).toFixed(2);
  const strAcc = (stats.sig_str_acc_total || 0).toFixed(1);
  const strDef = (stats.sig_str_def_total || 0).toFixed(1);
  const knockdowns = Math.round(stats.total_knockdowns || 0);
  
  // Grappling stats
  const tdAvg = (stats.td_avg_total || 0).toFixed(2);
  const tdAcc = (stats.td_acc_total || 0).toFixed(1);
  const tdDef = (stats.td_def_total || 0).toFixed(1);
  const subAvg = (stats.sub_avg_total || 0).toFixed(2);
  
  return (
    <div className="fighter-profile-page">
      <div className="container">
        {/* Back Button */}
        <Button 
          variant="ghost" 
          icon={<span>←</span>}
          onClick={() => navigate('/fighters')}
          className="back-button"
        >
          Back to Fighters
        </Button>
        
        {/* Fighter Header */}
        <Card variant="elevated" className="fighter-header">
          <div className="header-content">
            {/* Fighter Avatar */}
            <div className="fighter-avatar-large">
              <img 
                src={getFighterImage(fighter.name, stats.weight_class)}
                alt={fighter.name}
                />
            </div>
            
            {/* Fighter Info */}
            <div className="fighter-header-info">
              <h1 className="fighter-name-large">{fighter.name}</h1>
              
              <div className="fighter-badges">
                <span 
                  className="weight-class-badge"
                  style={{ 
                    background: colors.bg,
                    borderColor: colors.primary,
                    color: colors.primary
                  }}
                >
                  {weightClass}
                </span>
              </div>
              
              <div className="fighter-vitals">
                <div className="vital-item">
                  <span className="vital-label">Record</span>
                  <span className="vital-value">{wins}-{losses}-{draws}</span>
                </div>
                <div className="vital-divider"></div>
                <div className="vital-item">
                  <span className="vital-label">Age</span>
                  <span className="vital-value">{age}</span>
                </div>
                <div className="vital-divider"></div>
                <div className="vital-item">
                  <span className="vital-label">Height</span>
                  <span className="vital-value">{height}</span>
                </div>
                <div className="vital-divider"></div>
                <div className="vital-item">
                  <span className="vital-label">Reach</span>
                  <span className="vital-value">{reach}</span>
                </div>
                <div className="vital-divider"></div>
                <div className="vital-item">
                  <span className="vital-label">Weight</span>
                  <span className="vital-value">{weight}</span>
                </div>
              </div>
            </div>
          </div>
        </Card>
        
        {/* Stats Grid */}
        <div className="stats-grid">
          {/* Striking Stats */}
          <Card variant="glass" className="stat-card striking-card">
            <div className="stat-card-header">
              <span className="stat-icon">👊</span>
              <h3>Striking</h3>
            </div>
            <div className="stat-rows">
              <div className="stat-row">
                <span className="stat-label">Sig. Strikes Landed/Min</span>
                <span className="stat-value">{slpm}</span>
              </div>
              <div className="stat-row">
                <span className="stat-label">Striking Accuracy</span>
                <span className="stat-value">{strAcc}%</span>
              </div>
              <div className="stat-row">
                <span className="stat-label">Strike Defense</span>
                <span className="stat-value">{strDef}%</span>
              </div>
              <div className="stat-row">
                <span className="stat-label">Total Knockdowns</span>
                <span className="stat-value">{knockdowns}</span>
              </div>
            </div>
          </Card>
          
          {/* Grappling Stats */}
          <Card variant="glass" className="stat-card grappling-card">
            <div className="stat-card-header">
              <span className="stat-icon">🤼</span>
              <h3>Grappling</h3>
            </div>
            <div className="stat-rows">
              <div className="stat-row">
                <span className="stat-label">Takedowns/15min</span>
                <span className="stat-value">{tdAvg}</span>
              </div>
              <div className="stat-row">
                <span className="stat-label">Takedown Accuracy</span>
                <span className="stat-value">{tdAcc}%</span>
              </div>
              <div className="stat-row">
                <span className="stat-label">Takedown Defense</span>
                <span className="stat-value">{tdDef}%</span>
              </div>
              <div className="stat-row">
                <span className="stat-label">Submissions/15min</span>
                <span className="stat-value">{subAvg}</span>
              </div>
            </div>
          </Card>
          
          {/* Career Stats */}
          <Card variant="glass" className="stat-card career-card">
            <div className="stat-card-header">
              <span className="stat-icon">🏆</span>
              <h3>Career</h3>
            </div>
            <div className="stat-rows">
              <div className="stat-row">
                <span className="stat-label">Total Fights</span>
                <span className="stat-value">{wins + losses + draws}</span>
              </div>
              <div className="stat-row">
                <span className="stat-label">Win Rate</span>
                <span className="stat-value">{wins > 0 ? ((wins / (wins + losses)) * 100).toFixed(1) : 0}%</span>
              </div>
              <div className="stat-row">
                <span className="stat-label">Total Wins</span>
                <span className="stat-value">{wins}</span>
              </div>
              <div className="stat-row">
                <span className="stat-label">Total Losses</span>
                <span className="stat-value">{losses}</span>
              </div>
            </div>
          </Card>
          
          {/* Physical Stats */}
          <Card variant="glass" className="stat-card physical-card">
            <div className="stat-card-header">
              <span className="stat-icon">📏</span>
              <h3>Physical</h3>
            </div>
            <div className="stat-rows">
              <div className="stat-row">
                <span className="stat-label">Age</span>
                <span className="stat-value">{age} years</span>
              </div>
              <div className="stat-row">
                <span className="stat-label">Height</span>
                <span className="stat-value">{height}</span>
              </div>
              <div className="stat-row">
                <span className="stat-label">Reach</span>
                <span className="stat-value">{reach}</span>
              </div>
              <div className="stat-row">
                <span className="stat-label">Weight</span>
                <span className="stat-value">{weight}</span>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default FighterProfile;
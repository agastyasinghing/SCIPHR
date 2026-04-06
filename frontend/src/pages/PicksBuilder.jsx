import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import api from '../api/api';
import FighterSearchModal from '../components/picks/FighterSearchModal';
import FightPoster from '../components/picks/FightPoster';
import AnalystMode from '../components/picks/AnalystMode';
import './PicksBuilder.css';

/**
 * Picks Builder Page
 * Supports pre-loading fighters via URL params:
 *   /picks?fighter1=Fighter+Name
 *   /picks?fighter1=Fighter+A&fighter2=Fighter+B
 */
const PicksBuilder = () => {
  const [searchParams] = useSearchParams();
  const [mode, setMode] = useState('poster'); // 'poster' or 'analyst'
  const [fighter1, setFighter1] = useState(null);
  const [fighter2, setFighter2] = useState(null);
  const [prediction, setPrediction] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showSearchModal, setShowSearchModal] = useState(false);
  const [selectingFighter, setSelectingFighter] = useState(null); // 1 or 2

  // Pre-load fighters from URL params (?fighter1=Name&fighter2=Name)
  useEffect(() => {
    const f1Name = searchParams.get('fighter1');
    const f2Name = searchParams.get('fighter2');
    const load = async (name, setter) => {
      if (!name) return;
      try {
        const result = await api.getFighterProfile(name);
        setter(result);
      } catch {
        // Silently skip unresolvable names — user can select manually
      }
    };
    load(f1Name, setFighter1);
    load(f2Name, setFighter2);
  }, []); // run once on mount only
  
  const handleSelectFighter = (position) => {
    setSelectingFighter(position);
    setShowSearchModal(true);
  };
  
  const handleFighterSelected = (fighter) => {
    if (selectingFighter === 1) {
      setFighter1(fighter);
    } else {
      setFighter2(fighter);
    }
    setShowSearchModal(false);
    setSelectingFighter(null);
    
    // Reset prediction when fighters change
    setPrediction(null);
  };
  
  const handleGeneratePrediction = async () => {
    if (!fighter1 || !fighter2) return;

    setLoading(true);
    setError(null);
    try {
      const data = await api.predictFight(fighter1.name, fighter2.name);
      setPrediction(data);
    } catch (err) {
      const msg = err?.message?.includes('400')
        ? 'Cannot predict a fighter against themselves.'
        : 'Prediction failed. Check your connection and try again.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setFighter1(null);
    setFighter2(null);
    setPrediction(null);
    setError(null);
  };
  
  return (
    <div className="picks-builder-page">
      <div className="container">
        {/* Header */}
        <div className="picks-header">
          <h1 className="picks-title">
            <span className="title-icon">🥊</span>
            Picks Builder
          </h1>
          <p className="picks-subtitle">
            Create your prediction and share it with the world
          </p>
        </div>
        
        {/* Mode Toggle */}
        <div className="mode-toggle">
          <button
            className={`mode-btn ${mode === 'poster' ? 'active' : ''}`}
            onClick={() => setMode('poster')}
          >
            <span className="mode-icon">🎨</span>
            <span>Poster Mode</span>
          </button>
          <button
            className={`mode-btn ${mode === 'analyst' ? 'active' : ''}`}
            onClick={() => setMode('analyst')}
          >
            <span className="mode-icon">📊</span>
            <span>Analyst Mode</span>
          </button>
        </div>
        
        {/* Reset Button */}
        {(fighter1 || fighter2) && (
          <button className="reset-btn" onClick={handleReset}>
            <span>↻</span> Start Over
          </button>
        )}

        {/* Prediction Error */}
        {error && (
          <div className="prediction-error" role="alert">
            {error}
          </div>
        )}
        
        {/* Content */}
        <div className="picks-content">
          {mode === 'poster' ? (
            <FightPoster
              fighter1={fighter1}
              fighter2={fighter2}
              prediction={prediction}
              loading={loading}
              onSelectFighter={handleSelectFighter}
              onGeneratePrediction={handleGeneratePrediction}
            />
          ) : (
            <AnalystMode
              fighter1={fighter1}
              fighter2={fighter2}
              prediction={prediction}
              loading={loading}
              onSelectFighter={handleSelectFighter}
              onGeneratePrediction={handleGeneratePrediction}
            />
          )}
        </div>
      </div>
      
      {/* Fighter Search Modal */}
      {showSearchModal && (
        <FighterSearchModal
          onClose={() => setShowSearchModal(false)}
          onSelect={handleFighterSelected}
          excludeFighter={selectingFighter === 1 ? fighter2 : fighter1}
        />
      )}
    </div>
  );
};

export default PicksBuilder;
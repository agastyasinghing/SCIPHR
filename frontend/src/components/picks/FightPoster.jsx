import React, { useRef, useState } from 'react';
import api from '../../api/api';
import html2canvas from 'html2canvas';
import Button from '../shared/Button';
import './FightPoster.css';
import { getFighterImage } from '../../utils/imageUtils';
import AnalystMode from './AnalystMode';

/**
 * Fight Poster Component
 * Creates UFC-style fight poster with dynamic design + AI generation
 */
const FightPoster = ({ 
  fighter1, 
  fighter2, 
  prediction, 
  loading,
  onSelectFighter,
  onGeneratePrediction 
}) => {
  const posterRef = useRef(null);
  
  // AI Poster states
  const [aiPosterUrl, setAiPosterUrl] = useState(null);
  const [aiPosterStyle, setAiPosterStyle] = useState(null);
  const [generatingAI, setGeneratingAI] = useState(false);
  const [showAIPoster, setShowAIPoster] = useState(false);
  const [aiGenerationsLeft, setAiGenerationsLeft] = useState(1);
  const [aiPosterError, setAiPosterError] = useState(null);
  
  // Analyst Mode state
  const [showAnalystMode, setShowAnalystMode] = useState(false);
  
  // Weight class colors for dynamic theming
  const weightClassColors = {
    'Strawweight': { primary: '#EC4899', secondary: '#BE185D', gradient: 'linear-gradient(135deg, #BE185D, #EC4899)' },
    'Flyweight': { primary: '#8B5CF6', secondary: '#6D28D9', gradient: 'linear-gradient(135deg, #6D28D9, #8B5CF6)' },
    'Bantamweight': { primary: '#3B82F6', secondary: '#1D4ED8', gradient: 'linear-gradient(135deg, #1D4ED8, #3B82F6)' },
    'Featherweight': { primary: '#06B6D4', secondary: '#0E7490', gradient: 'linear-gradient(135deg, #0E7490, #06B6D4)' },
    'Lightweight': { primary: '#10B981', secondary: '#047857', gradient: 'linear-gradient(135deg, #047857, #10B981)' },
    'Welterweight': { primary: '#FACC15', secondary: '#CA8A04', gradient: 'linear-gradient(135deg, #CA8A04, #FACC15)' },
    'Middleweight': { primary: '#F59E0B', secondary: '#D97706', gradient: 'linear-gradient(135deg, #D97706, #F59E0B)' },
    'Light Heavyweight': { primary: '#EF4444', secondary: '#B91C1C', gradient: 'linear-gradient(135deg, #B91C1C, #EF4444)' },
    'Heavyweight': { primary: '#7C3AED', secondary: '#5B21B6', gradient: 'linear-gradient(135deg, #5B21B6, #7C3AED)' },
  };
  
  const f1Color = fighter1?.stats?.weight_class ? weightClassColors[fighter1.stats.weight_class] : weightClassColors['Welterweight'];
  const f2Color = fighter2?.stats?.weight_class ? weightClassColors[fighter2.stats.weight_class] : weightClassColors['Welterweight'];
  
  const handleDownload = async () => {
    if (!posterRef.current) return;
    
    try {
      const canvas = await html2canvas(posterRef.current, {
        backgroundColor: '#0A0E14',
        scale: 2,
      });
      
      const link = document.createElement('a');
      link.download = `sciphr-${fighter1?.name}-vs-${fighter2?.name}.png`.replace(/ /g, '-');
      link.href = canvas.toDataURL('image/png');
      link.click();
    } catch (error) {
      console.error('Failed to download poster:', error);
    }
  };
  
  const handleGenerateAIPoster = async () => {
    if (!fighter1 || !fighter2 || !prediction) return;
    
    setGeneratingAI(true);
    setAiPosterError(null);

    try {
      const data = await api.request('/generate-ai-poster', {
        method: 'POST',
        body: JSON.stringify({
          fighter1_name: fighter1.name,
          fighter2_name: fighter2.name,
          prediction: {
            winner: prediction.winner,
            confidence: prediction.confidence
          }
        }),
      });

      if (data.success) {
        setAiPosterUrl(data.image_url);
        setAiPosterStyle(data.style_name);
        setShowAIPoster(true);
        setAiGenerationsLeft(prev => Math.max(0, prev - 1));
        console.log('AI Poster generated:', data);
      } else {
        console.error('AI Poster generation failed:', data.error);
        setAiPosterError('Failed to generate AI poster. Please try again.');
      }
    } catch (error) {
      console.error('AI Poster error:', error);
      setAiPosterError('Error generating AI poster. Please try again.');
    } finally {
      setGeneratingAI(false);
    }
  };
  
  const canPredict = fighter1 && fighter2 && !prediction;
  const bothSelected = fighter1 && fighter2;
  
  return (
    <div className="fight-poster-container">
      {/* Show Analyst Mode OR Poster */}
      {showAnalystMode ? (
        // 📊 ANALYST MODE
        <AnalystMode 
          fighter1={fighter1}
          fighter2={fighter2}
          prediction={prediction}
        />
      ) : (
        // POSTER VIEW
        <>
          {showAIPoster && aiPosterUrl ? (
            // ✨ AI GENERATED POSTER
            <div className="ai-poster-display">
              <img 
                src={aiPosterUrl} 
                alt="AI Generated Fight Poster" 
                className="ai-poster-image"
                style={{
                  width: '100%',
                  maxWidth: '800px',
                  borderRadius: 'var(--radius-xl)',
                  border: '3px solid var(--accent-yellow)',
                  boxShadow: '0 0 50px rgba(250, 204, 21, 0.5)',
                  display: 'block',
                  margin: '0 auto'
                }}
              />
            </div>
          ) : (
            // 📊 CSS POSTER
            <div 
              ref={posterRef}
              className={`fight-poster ${prediction ? 'has-prediction' : ''}`}
              style={{
                background: bothSelected 
                  ? `linear-gradient(120deg, ${f1Color.secondary}20 0%, transparent 50%, ${f2Color.secondary}20 100%), 
                     radial-gradient(ellipse at top, ${f1Color.primary}15, transparent 50%),
                     radial-gradient(ellipse at bottom, ${f2Color.primary}15, transparent 50%),
                     linear-gradient(180deg, #0A0E14 0%, #1a1f2e 100%)`
                  : 'linear-gradient(180deg, #0A0E14 0%, #1a1f2e 100%)'
              }}
            >
              {/* Background Pattern */}
              <div className="poster-pattern"></div>
              
              {/* Header */}
              <div className="poster-header">
                <div className="poster-logo">SCIPHR</div>
                <div className="poster-event-title">
                  {prediction?.intelligence?.cinematic_title?.title || 'FIGHT NIGHT'}
                </div>
                {prediction?.intelligence?.cinematic_title?.subtitle && (
                  <div className="poster-event-subtitle">
                    {prediction.intelligence.cinematic_title.subtitle}
                  </div>
                )}
              </div>
              
              {/* Fighters */}
              <div className="poster-fighters">
                {/* Fighter 1 */}
                <div 
                  className={`poster-fighter left ${!fighter1 ? 'empty' : ''} ${prediction && prediction.winner === fighter1?.name ? 'winner' : ''} ${prediction && prediction.winner !== fighter1?.name ? 'loser' : ''}`}
                  onClick={() => !fighter1 && onSelectFighter(1)}
                  style={{
                    '--fighter-color': f1Color.primary,
                    '--fighter-glow': `0 0 60px ${f1Color.primary}80`
                  }}
                >
                  {fighter1 ? (
                    <>
                      <div className="fighter-image-container">
                        <img 
                          src={getFighterImage(fighter1.name, fighter1.stats.weight_class)}
                          alt={fighter1.name}
                          className="fighter-image"
                        />
                        <div className="fighter-glow" style={{ background: f1Color.gradient }}></div>
                      </div>
                      <div className="fighter-details">
                        <div className="fighter-name">{fighter1.name}</div>
                        <div className="fighter-record">{Math.round(fighter1.stats.wins_total)}-{Math.round(fighter1.stats.losses_total)}-{Math.round(fighter1.stats.draw)}</div>
                        <div className="fighter-class" style={{ borderColor: f1Color.primary, color: f1Color.primary }}>
                          {fighter1.stats.weight_class}
                        </div>
                      </div>
                    </>
                  ) : (
                    <div className="empty-slot">
                      <div className="empty-icon">+</div>
                      <div className="empty-text">SELECT<br/>FIGHTER 1</div>
                    </div>
                  )}
                </div>
                
                {/* VS Logo */}
                <div className="vs-container">
                  <div className="vs-logo">
                    <span>VS</span>
                  </div>
                  {bothSelected && !prediction && (
                    <div className="vs-spark"></div>
                  )}
                </div>
                
                {/* Fighter 2 */}
                <div 
                  className={`poster-fighter right ${!fighter2 ? 'empty' : ''} ${prediction && prediction.winner === fighter2?.name ? 'winner' : ''} ${prediction && prediction.winner !== fighter2?.name ? 'loser' : ''}`}
                  onClick={() => !fighter2 && onSelectFighter(2)}
                  style={{
                    '--fighter-color': f2Color.primary,
                    '--fighter-glow': `0 0 60px ${f2Color.primary}80`
                  }}
                >
                  {fighter2 ? (
                    <>
                      <div className="fighter-image-container">
                        <img 
                          src={getFighterImage(fighter2.name, fighter2.stats.weight_class)}
                          alt={fighter2.name}
                          className="fighter-image"
                        />
                        <div className="fighter-glow" style={{ background: f2Color.gradient }}></div>
                      </div>
                      <div className="fighter-details">
                        <div className="fighter-name">{fighter2.name}</div>
                        <div className="fighter-record">{Math.round(fighter2.stats.wins_total)}-{Math.round(fighter2.stats.losses_total)}-{Math.round(fighter2.stats.draw)}</div>
                        <div className="fighter-class" style={{ borderColor: f2Color.primary, color: f2Color.primary }}>
                          {fighter2.stats.weight_class}
                        </div>
                      </div>
                    </>
                  ) : (
                    <div className="empty-slot">
                      <div className="empty-icon">+</div>
                      <div className="empty-text">SELECT<br/>FIGHTER 2</div>
                    </div>
                  )}
                </div>
              </div>
              
              {/* Prediction Stamp */}
              {prediction && (
                <div className="prediction-stamp">
                  <div className="stamp-border">
                    <div className="stamp-content">
                      <div className="stamp-label">PREDICTION</div>
                      <div className="stamp-winner">{prediction.winner || 'Unknown'}</div>
                      <div className="stamp-confidence">
                        {prediction.confidence 
                          ? `${(parseFloat(prediction.confidence) * 100).toFixed(1)}%`
                          : 'N/A'}
                      </div>
                      <div className="stamp-model">SCIPHR AI</div>
                    </div>
                  </div>
                </div>
              )}
              
              {/* Intelligence Badges */}
              {prediction?.intelligence?.badges?.length > 0 && (
                <div className="poster-badges">
                  {prediction.intelligence.badges.map((badge) => (
                    <span
                      key={`${badge.key}-${badge.fighter}`}
                      className={`poster-badge poster-badge--${badge.color}`}
                      title={badge.reason}
                    >
                      {badge.label}
                    </span>
                  ))}
                </div>
              )}

              {/* Footer */}
              <div className="poster-footer">
                <div className="poster-location">
                  <span className="location-icon">📍</span>
                  <span>Generated by SCIPHR.ai</span>
                </div>
              </div>
            </div>
          )}
        </>
      )}
      
      {/* Action Buttons */}
      <div className="poster-actions">
        {canPredict && (
          <Button
            variant="primary"
            size="large"
            onClick={onGeneratePrediction}
            disabled={loading}
            className="analyze-btn"
          >
            {loading ? '⚡ Analyzing...' : '🔮 Generate Prediction'}
          </Button>
        )}

        {/* Analyst Mode Toggle */}
        {prediction && !showAnalystMode && (
          <Button
            variant="secondary"
            size="large"
            onClick={() => setShowAnalystMode(true)}
            icon={<span>📊</span>}
          >
            View Analyst Mode
          </Button>
        )}

        {showAnalystMode && (
          <Button
            variant="secondary"
            size="large"
            onClick={() => setShowAnalystMode(false)}
            icon={<span>📋</span>}
          >
            Back to Poster
          </Button>
        )}
        
        {prediction && !showAnalystMode && (
          <>
            {/* AI Poster Generation */}
            {!showAIPoster && aiGenerationsLeft > 0 && (
              <Button
                variant="primary"
                size="large"
                onClick={handleGenerateAIPoster}
                disabled={generatingAI}
                className="ai-poster-btn"
              >
                {generatingAI ? '✨ Creating Magic...' : `✨ Generate AI Poster (${aiGenerationsLeft} left)`}
              </Button>
            )}
            
            {aiPosterError && (
              <div className="ai-poster-error" style={{ color: '#EF4444', fontSize: '0.875rem', marginTop: '0.5rem' }}>
                {aiPosterError}
              </div>
            )}

            {!showAIPoster && aiGenerationsLeft === 0 && (
              <div className="upgrade-message">
                <p>🔒 Out of free AI poster generations today</p>
                <Button variant="primary" size="small">
                  Upgrade to Premium for Unlimited
                </Button>
              </div>
            )}
            
            {/* Toggle between CSS and AI poster */}
            {aiPosterUrl && (
              <div className="poster-toggle">
                <Button
                  variant={!showAIPoster ? 'primary' : 'secondary'}
                  onClick={() => setShowAIPoster(false)}
                >
                  📊 CSS Poster
                </Button>
                <Button
                  variant={showAIPoster ? 'primary' : 'secondary'}
                  onClick={() => setShowAIPoster(true)}
                >
                  ✨ AI Poster
                </Button>
                {aiPosterStyle && (
                  <span className="style-badge">Style: {aiPosterStyle}</span>
                )}
              </div>
            )}
            
            <div className="poster-actions-row">
              <Button
                variant="secondary"
                onClick={handleDownload}
                icon={<span>⬇️</span>}
              >
                Download Poster
              </Button>
              <Button
                variant="secondary"
                icon={<span>🐦</span>}
                onClick={() => {
                  const text = `My SCIPHR prediction: ${prediction.winner} wins with ${(prediction.confidence * 100).toFixed(1)}% confidence! 🥊 #UFC #MMA`;
                  window.open(`https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=https://sciphr.ai`, '_blank');
                }}
              >
                Share on X
              </Button>
              
              {/* Regenerate AI Poster */}
              {showAIPoster && aiGenerationsLeft > 0 && (
                <Button
                  variant="secondary"
                  onClick={handleGenerateAIPoster}
                  disabled={generatingAI}
                  icon={<span>🔄</span>}
                >
                  {generatingAI ? 'Regenerating...' : 'New Style'}
                </Button>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default FightPoster;
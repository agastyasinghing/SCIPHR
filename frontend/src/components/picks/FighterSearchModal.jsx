import React, { useState, useEffect } from 'react';
import api from '../../api/api';
import Card from '../shared/Card';
import './FighterSearchModal.css';

/**
 * Fighter Search Modal
 * Search and select fighters for picks builder
 */
const FighterSearchModal = ({ onClose, onSelect, excludeFighter }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [fighters, setFighters] = useState([]);
  const [filteredFighters, setFilteredFighters] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedFighter, setSelectedFighter] = useState(null);
  
  useEffect(() => {
    loadFighters();
  }, []);
  
  useEffect(() => {
    // fighters is now [{name, weight_class, is_active}]
    const excludeName = excludeFighter?.name ?? '';
    const filter = (f) => f.name !== excludeName;

    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      setFilteredFighters(
        fighters.filter(f => f.name.toLowerCase().includes(query) && filter(f)).slice(0, 50)
      );
    } else {
      setFilteredFighters(fighters.filter(filter).slice(0, 50));
    }
  }, [searchQuery, fighters, excludeFighter]);

  const loadFighters = async () => {
    setLoading(true);
    try {
      const result = await api.getFighters('', 10000);
      setFighters(result.fighters || []);
      setFilteredFighters((result.fighters || []).slice(0, 50));
    } catch (error) {
      console.error('Failed to load fighters:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectFighter = async (fighterName) => {
    setSelectedFighter(fighterName);

    // Load fighter stats
    try {
      const result = await api.getFighterProfile(fighterName);
      onSelect(result);
    } catch (error) {
      console.error('Failed to load fighter stats:', error);
    }
  };
  
  return (
    <div className="fighter-search-modal-overlay" onClick={onClose}>
      <div className="fighter-search-modal" onClick={(e) => e.stopPropagation()}>
        <Card variant="elevated" className="modal-card">
          {/* Header */}
          <div className="modal-header">
            <h2>Select Fighter</h2>
            <button className="modal-close" onClick={onClose}>✕</button>
          </div>
          
          {/* Search */}
          <div className="modal-search">
            <span className="search-icon">🔍</span>
            <input
              type="text"
              placeholder="Search fighters..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              autoFocus
              className="search-input"
            />
          </div>
          
          {/* Results */}
          <div className="modal-results">
            {loading ? (
              <div className="loading-state">
                <div className="loading-spinner"></div>
                <p>Loading fighters...</p>
              </div>
            ) : filteredFighters.length === 0 ? (
              <div className="empty-state">
                <span className="empty-icon">🤷</span>
                <p>No fighters found</p>
              </div>
            ) : (
              <div className="fighters-list">
                {filteredFighters.map((fighter, idx) => (
                  <div
                    key={idx}
                    className={`fighter-item ${selectedFighter === fighter.name ? 'selected' : ''}`}
                    onClick={() => handleSelectFighter(fighter.name)}
                  >
                    <div className="fighter-avatar-small">
                      {fighter.name.charAt(0)}
                    </div>
                    <div className="fighter-name-small">{fighter.name}</div>
                    <div className="fighter-arrow">→</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
};

export default FighterSearchModal;
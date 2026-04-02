import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import api from '../api/api';
import Card from '../components/shared/Card';
import './FighterSearch.css';

/**
 * Fighter Search Page
 * Browse and search fighter database
 */
const FighterSearch = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [searchQuery, setSearchQuery] = useState(searchParams.get('search') || '');
  const [fighters, setFighters] = useState([]);
  const [filteredFighters, setFilteredFighters] = useState([]);
  const [loading, setLoading] = useState(false);
  const [weightClassFilter, setWeightClassFilter] = useState('all');
  const [sortBy, setSortBy] = useState('name');
  
  const weightClasses = [
    'all',
    'Flyweight',
    'Bantamweight',
    'Featherweight',
    'Lightweight',
    'Welterweight',
    'Middleweight',
    'Light Heavyweight',
    'Heavyweight',
  ];
  
  const sortOptions = [
    { value: 'name', label: 'Name (A-Z)' },
    { value: 'name-desc', label: 'Name (Z-A)' },
  ];
  
  // Load all fighters on mount
  useEffect(() => {
    loadFighters();
  }, []);
  
  // Filter and sort fighters
  useEffect(() => {
    let filtered = [...fighters];
    
    // Filter by search query
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(fighter => 
        fighter.toLowerCase().includes(query)
      );
    }
    
    // Sort
    if (sortBy === 'name') {
      filtered.sort((a, b) => a.localeCompare(b));
    } else if (sortBy === 'name-desc') {
      filtered.sort((a, b) => b.localeCompare(a));
    }
    
    setFilteredFighters(filtered);
  }, [searchQuery, fighters, weightClassFilter, sortBy]);
  
  const loadFighters = async () => {
    setLoading(true);
    try {
      // Load ALL fighters - increase limit or make multiple requests
      const result = await api.getFighters('', 10000); // Request way more
      setFighters(result.fighters || []);
      setFilteredFighters(result.fighters || []);
    } catch (error) {
      console.error('Failed to load fighters:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const handleFighterClick = (fighter) => {
    // Navigate to fighter profile page
    navigate(`/fighter/${encodeURIComponent(fighter)}`);
  };
  
  return (
    <div className="fighter-search-page">
      <div className="container">
        {/* Header */}
        <div className="search-header">
          <h1>🥊 Fighter Database</h1>
          <p className="search-subtitle">
            Browse and search our complete database of {fighters.length} UFC fighters
          </p>
        </div>
        
        {/* Search & Filters */}
        <Card variant="glass" className="search-controls">
          <div className="search-bar-large">
            <span className="search-icon">🔍</span>
            <input
              type="text"
              placeholder="Search fighters by name..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="search-input-large"
            />
            {searchQuery && (
              <button 
                className="clear-search"
                onClick={() => setSearchQuery('')}
              >
                ✕
              </button>
            )}
          </div>
          
          <div className="filters">
            <div className="filter-group">
              <label className="filter-label">Weight Class</label>
              <select 
                className="filter-select"
                value={weightClassFilter}
                onChange={(e) => setWeightClassFilter(e.target.value)}
              >
                {weightClasses.map(wc => (
                  <option key={wc} value={wc}>
                    {wc === 'all' ? 'All Weight Classes' : wc}
                  </option>
                ))}
              </select>
            </div>
            
            <div className="filter-group">
              <label className="filter-label">Sort By</label>
              <select 
                className="filter-select"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
              >
                {sortOptions.map(opt => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
            
            <div className="filter-stats">
              <span className="stat-chip">
                <span className="stat-value">{filteredFighters.length}</span>
                <span className="stat-label">Fighters</span>
              </span>
            </div>
          </div>
        </Card>
        
        {/* Results */}
        <div className="search-results">
          {loading ? (
            <div className="loading-state">
              <div className="loading-spinner"></div>
              <p>Loading fighters...</p>
            </div>
          ) : filteredFighters.length === 0 ? (
            <div className="empty-state">
              <span className="empty-icon">🤷</span>
              <h3>No fighters found</h3>
              <p>Try adjusting your search or filters</p>
            </div>
          ) : (
            <div className="fighters-grid">
              {filteredFighters.map((fighter, idx) => (
                <Card
                  key={idx}
                  variant="glass"
                  hover={true}
                  className="fighter-card"
                  onClick={() => handleFighterClick(fighter)}
                >
                  <div className="fighter-card-content">
                    <div className="fighter-avatar">
                      {fighter.charAt(0)}
                    </div>
                    <div className="fighter-info">
                      <h4 className="fighter-name">{fighter}</h4>
                      <p className="fighter-meta">Click to view profile</p>
                    </div>
                    <div className="fighter-arrow">→</div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default FighterSearch;
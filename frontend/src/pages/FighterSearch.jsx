import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import api from '../api/api';
import Card from '../components/shared/Card';
import './FighterSearch.css';

const WEIGHT_CLASS_COLORS = {
  'Strawweight':       '#EC4899',
  'Flyweight':         '#8B5CF6',
  'Bantamweight':      '#3B82F6',
  'Featherweight':     '#06B6D4',
  'Lightweight':       '#10B981',
  'Welterweight':      '#FACC15',
  'Middleweight':      '#F59E0B',
  'Light Heavyweight': '#EF4444',
  'Heavyweight':       '#7C3AED',
};

const WEIGHT_CLASSES = [
  'all',
  'Strawweight',
  'Flyweight',
  'Bantamweight',
  'Featherweight',
  'Lightweight',
  'Welterweight',
  'Middleweight',
  'Light Heavyweight',
  'Heavyweight',
];

/**
 * Fighter Search Page
 * Browse and search fighter database.
 * fighters is [{name, weight_class, is_active}] — weight class filter and
 * active/inactive filter both work client-side.
 */
const FighterSearch = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [searchQuery, setSearchQuery] = useState(searchParams.get('search') || '');
  const [fighters, setFighters] = useState([]);           // full list from API
  const [filteredFighters, setFilteredFighters] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState(null);
  const [weightClassFilter, setWeightClassFilter] = useState('all');
  const [activeFilter, setActiveFilter] = useState('all'); // 'all' | 'active' | 'inactive'
  const [sortBy, setSortBy] = useState('name');

  const sortOptions = [
    { value: 'name',      label: 'Name (A-Z)' },
    { value: 'name-desc', label: 'Name (Z-A)' },
  ];

  // Load all fighters on mount
  useEffect(() => {
    const loadFighters = async () => {
      setLoading(true);
      try {
        const result = await api.getFighters('', 5000); // backend Query le=5000; matches backend/main.py limit
        setFighters(result.fighters || []);
      } catch (error) {
        console.error('Failed to load fighters:', error);
        setLoadError('Failed to load fighter database. Check that the backend is running.');
      } finally {
        setLoading(false);
      }
    };
    loadFighters();
  }, []);

  // Filter + sort whenever inputs change
  useEffect(() => {
    let list = [...fighters];

    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      list = list.filter(f => f.name.toLowerCase().includes(q));
    }

    if (weightClassFilter !== 'all') {
      list = list.filter(f => f.weight_class === weightClassFilter);
    }

    if (activeFilter === 'active') {
      list = list.filter(f => f.is_active !== false);
    } else if (activeFilter === 'inactive') {
      list = list.filter(f => f.is_active === false);
    }

    if (sortBy === 'name') {
      list.sort((a, b) => a.name.localeCompare(b.name));
    } else if (sortBy === 'name-desc') {
      list.sort((a, b) => b.name.localeCompare(a.name));
    }

    setFilteredFighters(list);
  }, [searchQuery, fighters, weightClassFilter, activeFilter, sortBy]);

  const handleFighterClick = (fighter) => {
    navigate(`/fighter/${encodeURIComponent(fighter.name)}`);
  };

  const wcColor = (wc) => WEIGHT_CLASS_COLORS[wc] || '#6B7280';

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
              <button className="clear-search" onClick={() => setSearchQuery('')}>✕</button>
            )}
          </div>

          <div className="filters">
            {/* Weight Class */}
            <div className="filter-group">
              <label className="filter-label">Weight Class</label>
              <select
                className="filter-select"
                value={weightClassFilter}
                onChange={(e) => setWeightClassFilter(e.target.value)}
              >
                {WEIGHT_CLASSES.map(wc => (
                  <option key={wc} value={wc}>
                    {wc === 'all' ? 'All Weight Classes' : wc}
                  </option>
                ))}
              </select>
            </div>

            {/* Active / Inactive */}
            <div className="filter-group">
              <label className="filter-label">Status</label>
              <select
                className="filter-select"
                value={activeFilter}
                onChange={(e) => setActiveFilter(e.target.value)}
              >
                <option value="all">All Fighters</option>
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
              </select>
            </div>

            {/* Sort */}
            <div className="filter-group">
              <label className="filter-label">Sort By</label>
              <select
                className="filter-select"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
              >
                {sortOptions.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
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
          ) : loadError ? (
            <div className="empty-state">
              <div className="empty-icon">⚠️</div>
              <h3>Could not load fighters</h3>
              <p>{loadError}</p>
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
                    <div
                      className="fighter-avatar"
                      style={{ backgroundColor: `${wcColor(fighter.weight_class)}22`, color: wcColor(fighter.weight_class) }}
                    >
                      {fighter.name.charAt(0)}
                    </div>
                    <div className="fighter-info">
                      <h4 className="fighter-name">{fighter.name}</h4>
                      <div className="fighter-meta-row">
                        {fighter.weight_class && (
                          <span
                            className="fighter-weight-class-tag"
                            style={{ color: wcColor(fighter.weight_class), borderColor: `${wcColor(fighter.weight_class)}55` }}
                          >
                            {fighter.weight_class}
                          </span>
                        )}
                        {fighter.is_active === false && (
                          <span className="fighter-inactive-tag">Inactive</span>
                        )}
                      </div>
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

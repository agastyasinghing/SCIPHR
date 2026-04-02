import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './Navbar.css';

/**
 * Navbar Component
 * Main navigation with logo, links, and search
 */
const Navbar = () => {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearchFocused, setIsSearchFocused] = useState(false);
  
  const handleSearch = (e) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      navigate(`/fighters?search=${searchQuery}`);
    }
  };
  
  return (
    <nav className="navbar">
      <div className="navbar-container">
        {/* Logo */}
        <div className="navbar-logo" onClick={() => navigate('/')}>
          <div className="logo-icon">⚔️</div>
          <div className="logo-text">
            <span className="logo-name">SCIPHR</span>
            <span className="logo-tagline">AI Fight Predictions</span>
          </div>
        </div>
        
        {/* Navigation Links */}
        <div className="navbar-links">
          <button 
            className="nav-link"
            onClick={() => navigate('/')}
          >
            <span className="nav-icon">🏠</span>
            <span className="nav-label">Dashboard</span>
          </button>
          <button 
            className="nav-link"
            onClick={() => navigate('/picks')}
          >
            <span className="nav-icon">🎲</span>
            <span className="nav-label">Picks Builder</span>
          </button>
          <button 
            className="nav-link"
            onClick={() => navigate('/fighters')}
          >
            <span className="nav-icon">🥊</span>
            <span className="nav-label">Fighters</span>
          </button>
          <button 
            className="nav-link"
            onClick={() => console.log('Events - Coming soon!')}
          >
            <span className="nav-icon">📅</span>
            <span className="nav-label">Events</span>
          </button>
        </div>
        
        {/* Search Bar */}
        <form 
          className={`navbar-search ${isSearchFocused ? 'focused' : ''}`}
          onSubmit={handleSearch}
        >
          <span className="search-icon">🔍</span>
          <input
            type="text"
            placeholder="Search fighters, events..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onFocus={() => setIsSearchFocused(true)}
            onBlur={() => setIsSearchFocused(false)}
            className="search-input"
          />
          {searchQuery && (
            <button 
              type="button" 
              className="search-clear"
              onClick={() => setSearchQuery('')}
            >
              ✕
            </button>
          )}
        </form>
        
        {/* User Actions */}
        <div className="navbar-actions">
          <button className="action-btn notifications">
            <span className="action-icon">🔔</span>
            <span className="notification-badge">3</span>
          </button>
          <button className="action-btn settings">
            <span className="action-icon">⚙️</span>
          </button>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
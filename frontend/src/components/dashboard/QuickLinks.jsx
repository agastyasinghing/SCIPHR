import React from 'react';
import Card from '../shared/Card';
import './QuickLinks.css';

/**
 * Quick Links Component
 * Provides fast access to main features
 */
const QuickLinks = () => {
  const links = [
    {
      id: 'search',
      icon: '🔍',
      title: 'Search',
      description: 'Find fighters, events, and fights',
      color: 'yellow',
    },
    {
      id: 'analytics',
      icon: '📊',
      title: 'Analytics',
      description: 'Dive deep into fight data',
      color: 'cyan',
    },
    {
      id: 'picks',
      icon: '🎯',
      title: 'Picks Builder',
      description: 'Generate picks with our models',
      color: 'lime',
    },
    {
      id: 'rankings',
      icon: '🏆',
      title: 'Rankings',
      description: 'UFC fighter rankings',
      color: 'orange',
    },
  ];
  
  const handleLinkClick = (linkId) => {
    console.log(`Navigating to: ${linkId}`);
    // TODO: Implement navigation
  };
  
  return (
    <div className="quick-links-section">
      <div className="quick-links-grid">
        {links.map((link) => (
          <Card
            key={link.id}
            variant="glass"
            hover={true}
            className={`quick-link-card quick-link-${link.color}`}
            onClick={() => handleLinkClick(link.id)}
          >
            <div className="quick-link-icon">{link.icon}</div>
            <h3 className="quick-link-title">{link.title}</h3>
            <p className="quick-link-description">{link.description}</p>
          </Card>
        ))}
      </div>
    </div>
  );
};

export default QuickLinks;

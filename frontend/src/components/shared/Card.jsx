import React from 'react';
import './Card.css';

/**
 * Reusable Card Component
 * Glass morphism styled card with optional glow effects
 */
const Card = ({ 
  children, 
  variant = 'glass', 
  glow = false,
  glowColor = 'yellow',
  hover = false,
  className = '',
  onClick,
  ...props 
}) => {
  const baseClass = 'card';
  const variantClass = `card-${variant}`;
  const glowClass = glow ? `card-glow card-glow-${glowColor}` : '';
  const hoverClass = hover ? 'card-hover' : '';
  const clickableClass = onClick ? 'card-clickable' : '';
  
  const cardClass = `${baseClass} ${variantClass} ${glowClass} ${hoverClass} ${clickableClass} ${className}`.trim();
  
  return (
    <div 
      className={cardClass}
      onClick={onClick}
      {...props}
    >
      {children}
    </div>
  );
};

export default Card;

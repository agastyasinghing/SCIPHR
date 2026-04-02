/**
 * Fighter Image Utilities
 * Handles fighter images with fallback to avatars
 */

// Import the fighter images mapping
import fighterImagesMapping from '../../public/fighters/fighter_images.json';

/**
 * Get fighter image URL with fallback
 * @param {string} fighterName - Fighter's full name
 * @param {string} weightClass - Fighter's weight class (for avatar color)
 * @returns {string} Image URL
 */
export const getFighterImage = (fighterName, weightClass = 'Welterweight') => {
  // Check if we have a real image
  if (fighterImagesMapping && fighterImagesMapping[fighterName]) {
    const imageData = fighterImagesMapping[fighterName];
    if (imageData && imageData.filename) {
      return `/fighters/${imageData.filename}`;
    }
  }
  
  // Fallback to UI Avatars
  const weightClassColors = {
    'Strawweight': 'EC4899',
    'Flyweight': '8B5CF6',
    'Bantamweight': '3B82F6',
    'Featherweight': '06B6D4',
    'Lightweight': '10B981',
    'Welterweight': 'FACC15',
    'Middleweight': 'F59E0B',
    'Light Heavyweight': 'EF4444',
    'Heavyweight': '7C3AED',
  };
  
  const color = weightClassColors[weightClass] || 'FACC15';
  
  return `https://ui-avatars.com/api/?name=${encodeURIComponent(fighterName)}&size=300&background=${color}&color=0A0E14&bold=true&font-size=0.35`;
};

/**
 * Check if fighter has a real image
 * @param {string} fighterName 
 * @returns {boolean}
 */
export const hasFighterImage = (fighterName) => {
  return !!(fighterImagesMapping && fighterImagesMapping[fighterName] && fighterImagesMapping[fighterName].filename);
};
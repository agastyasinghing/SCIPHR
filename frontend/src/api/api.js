/**
 * API Service for SCIPHR Backend
 * Handles all communication with FastAPI backend
 */

const _envUrl = import.meta.env.VITE_API_URL;

if (!_envUrl) {
  if (import.meta.env.DEV) {
    console.warn('[SCIPHR] VITE_API_URL not set — falling back to http://localhost:8000');
  } else {
    throw new Error('[SCIPHR] VITE_API_URL is required in production. Check your environment configuration.');
  }
}

const API_BASE_URL = _envUrl || 'http://localhost:8000';

// TODO (Phase 4): getFighterStats() and getFighterProfile() are duplicates —
// both call /fighter/:name. Remove getFighterStats() when all components are wired.

class APIService {
  /**
   * Generic fetch wrapper with error handling
   */
  async request(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    
    try {
      const response = await fetch(url, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
        ...options,
      });
      
      if (!response.ok) {
        throw new Error(`API Error: ${response.status} ${response.statusText}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error(`API request failed for ${endpoint}:`, error);
      throw error;
    }
  }
  
  /**
   * Health check
   */
  async healthCheck() {
    return this.request('/');
  }
  
  /**
   * Get list of fighters
   * @param {string} search - Optional search term
   * @param {number} limit - Max results to return
   */
  async getFighters(search = '', limit = 100) {
    const params = new URLSearchParams();
    if (search) params.append('search', search);
    if (limit) params.append('limit', limit);
    
    const query = params.toString() ? `?${params.toString()}` : '';
    return this.request(`/fighters${query}`);
  }

  /**
   * Get fighter details/stats
   * @param {string} fighterName - Fighter name
   */
  async getFighterProfile(fighterName) {
    return this.request(`/fighter/${encodeURIComponent(fighterName)}`);
  }
  
  /**
   * Get prediction for a fight
   * @param {string} fighter1 - First fighter name
   * @param {string} fighter2 - Second fighter name
   * @returns {Promise} Prediction result with AI analysis
   */
  async predictFight(fighter1, fighter2) {
    return this.request('/predict', {
      method: 'POST',
      body: JSON.stringify({
        fighter1,
        fighter2,
      }),
    });
  }
  
  /**
   * Search for a fighter (uses the /fighters endpoint with search)
   * @param {string} query - Search query
   * @returns {Promise} List of matching fighters
   */
  async searchFighters(query) {
    return this.getFighters(query, 10);
  }
  
  /**
   * Get fighter details/stats
   * @param {string} fighterName - Fighter name
   */
  async getFighterStats(fighterName) {
    return this.request(`/fighter/${encodeURIComponent(fighterName)}`);
  }
  
  /**
   * Get upcoming events
   */
  async getUpcomingEvents() {
    // TODO: Implement when backend endpoint is ready
    return this.request('/events/
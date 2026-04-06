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
        const err = new Error(`API Error: ${response.status} ${response.statusText}`);
        err.status = response.status;
        throw err;
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
   * Get list of fighters as objects: [{name, weight_class, is_active}]
   * @param {string} search - Optional search term
   * @param {number} limit - Max results to return
   * @param {string} weightClass - Optional weight class filter
   * @param {boolean} activeOnly - When true, only return active fighters
   */
  async getFighters(search = '', limit = 100, weightClass = '', activeOnly = false) {
    const params = new URLSearchParams();
    if (search) params.append('search', search);
    if (limit) params.append('limit', limit);
    if (weightClass) params.append('weight_class', weightClass);
    if (activeOnly) params.append('active_only', 'true');

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
   * Fast prediction without logging to predictions_log.
   * Returns {winner, confidence, prob_fighter1, prob_fighter2} only.
   * Use this for previews and auto-loaded display — never for user-initiated picks.
   */
  async predictSimple(fighter1, fighter2) {
    return this.request('/predict/simple', {
      method: 'POST',
      body: JSON.stringify({ fighter1, fighter2 }),
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
   * Get upcoming events
   */
  async getUpcomingEvents() {
    // TODO: Implement when backend endpoint is ready
    return this.request('/events/upcoming');
  }
  
  /**
   * Get past events
   */
  async getPastEvents() {
    // TODO: Implement when backend endpoint is ready
    return this.request('/events/past');
  }
  
  /**
   * Generate AI analysis for a fight (async — call after /predict renders)
   * @param {string} fighter1 - First fighter name
   * @param {string} fighter2 - Second fighter name
   * @param {object} predictionData - Full prediction result from predictFight()
   */
  async generateAIAnalysis(fighter1, fighter2, predictionData) {
    return this.request('/generate-ai-analysis', {
      method: 'POST',
      body: JSON.stringify({
        fighter1,
        fighter2,
        winner: predictionData.winner,
        confidence: predictionData.confidence,
        fighter1_stats: predictionData.fighter1_stats ?? {},
        fighter2_stats: predictionData.fighter2_stats ?? {},
      }),
    });
  }

  /**
   * Get prediction history (historical scorecard)
   * @param {number} limit - Max rows to return (default 50)
   * @param {number} offset - Pagination offset
   */
  async getHistoricalScorecard(limit = 50, offset = 0) {
    return this.request(`/historical-scorecard?limit=${limit}&offset=${offset}`);
  }

  /**
   * Get fight history for a single fighter (last 20 fights)
   * @param {string} fighterName - Fighter name (URL-encoded internally)
   */
  async getFighterHistory(fighterName) {
    return this.request(`/fighter/${encodeURIComponent(fighterName)}/history`);
  }

  /**
   * Run predict/simple for all fights on an event card.
   * Used by the Dashboard Upset Watch feed.
   * @param {number} eventId - Event ID from events.json
   */
  async getCardPredictions(eventId) {
    return this.request(`/events/${eventId}/card-predictions`);
  }
}

// Export singleton instance
export const api = new APIService();
export default api;
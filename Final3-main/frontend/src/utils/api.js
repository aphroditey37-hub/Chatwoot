/**
 * DEPRECATED - Use src/api/http.js instead
 * 
 * This file exists ONLY for backward compatibility.
 * All new code should import from '../api/http' or '../api'
 */

import http, { API_URL, API_V1 } from '../api/http';

// Re-export for backward compatibility
export const API_BASE = API_URL;
export { API_V1 };
export const apiClient = http;
export default http;

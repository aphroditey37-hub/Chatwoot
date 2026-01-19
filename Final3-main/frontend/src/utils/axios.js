/**
 * DEPRECATED - Use src/api/http.js instead
 * 
 * This file exists ONLY for backward compatibility.
 * All new code should import from '../api/http' or '../api'
 */

import http, { API_URL } from '../api/http';

// Re-export for backward compatibility
export const BACKEND_URL = API_URL;
export default http;

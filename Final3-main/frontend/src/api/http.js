/**
 * Centralized HTTP Client - SINGLE SOURCE OF TRUTH
 * All API calls MUST use this instance
 * 
 * Features:
 * - Automatic auth token injection
 * - Network error handling (520, timeout, unreachable)
 * - Never crashes UI with raw error objects
 * - Normalized error responses
 */

import axios from 'axios';

// Environment-based API URL - SINGLE SOURCE
// Use env variable if set, otherwise use current origin (platform handles routing via ingress)
const API_BASE_URL = process.env.REACT_APP_BACKEND_URL || '';

// Create axios instance with defaults
const http = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Request Interceptor
 * - Adds auth token to all requests
 * - Uses ONLY localStorage["token"]
 */
http.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(normalizeError(error));
  }
);

/**
 * Response Interceptor
 * - Handles network errors (520, timeout, unreachable)
 * - Normalizes all error responses
 * - NEVER redirects on 401 (let guards handle it)
 */
http.interceptors.response.use(
  (response) => response,
  (error) => {
    return Promise.reject(normalizeError(error));
  }
);

/**
 * Normalize any error into a safe, UI-friendly format
 * @returns {{ message: string, error_code: string, status?: number, isNetworkError: boolean, isAuthError: boolean }}
 */
function normalizeError(error) {
  // Network error (no response at all)
  if (!error.response) {
    const isTimeout = error.code === 'ECONNABORTED';
    const message = isTimeout 
      ? 'Request timed out. Please try again.'
      : 'Server temporarily unavailable. Please try again.';
    
    return {
      message,
      error_code: 'E_NET',
      status: 0,
      isNetworkError: true,
      isAuthError: false,
    };
  }

  const { status, data } = error.response;

  // 520 or other server errors
  if (status >= 500 || status === 520) {
    return {
      message: 'Server temporarily unavailable. Please try again.',
      error_code: 'E_SERVER',
      status,
      isNetworkError: true,
      isAuthError: false,
    };
  }

  // 401 Unauthorized
  if (status === 401) {
    return {
      message: 'Session expired. Please login again.',
      error_code: 'E_AUTH',
      status,
      isNetworkError: false,
      isAuthError: true,
    };
  }

  // 403 Forbidden
  if (status === 403) {
    return {
      message: 'Access denied.',
      error_code: 'E_FORBIDDEN',
      status,
      isNetworkError: false,
      isAuthError: false,
    };
  }

  // Extract message from response data
  const message = extractErrorMessage(data);

  return {
    message,
    error_code: 'E_API',
    status,
    isNetworkError: false,
    isAuthError: false,
    data,
  };
}

/**
 * Extract error message from various response formats
 * Priority: message > detail > error > fallback
 * Handles: string, object with detail, array of errors, nested objects
 */
function extractErrorMessage(data, fallback = 'Something went wrong. Please try again.') {
  if (!data) return fallback;
  
  // String response
  if (typeof data === 'string') return data;
  
  // Priority 1: message field (most common API response format)
  if (data.message && typeof data.message === 'string') {
    return data.message;
  }
  
  // Priority 2: FastAPI detail field
  if (data.detail) {
    if (typeof data.detail === 'string') return data.detail;
    
    // Pydantic validation errors (array)
    if (Array.isArray(data.detail)) {
      return data.detail
        .map(err => err.msg || err.message || String(err))
        .join(', ');
    }
    
    // Nested object
    if (typeof data.detail === 'object') {
      return data.detail.msg || data.detail.message || fallback;
    }
  }
  
  // Priority 3: error field
  if (data.error && typeof data.error === 'string') {
    return data.error;
  }
  
  return fallback;
}

/**
 * Safe API call wrapper
 * Prevents crashes and provides consistent error handling
 * 
 * @param {Promise} apiCall - The API call promise
 * @param {Object} options - Options for handling the response
 * @returns {Object} { data, error, success, isNetworkError }
 */
export async function safeApiCall(apiCall, options = {}) {
  const { defaultValue = null } = options;
  
  try {
    const response = await apiCall;
    return {
      data: response.data,
      error: null,
      success: true,
      isNetworkError: false,
    };
  } catch (error) {
    return {
      data: defaultValue,
      error: error.message || 'An error occurred',
      success: false,
      isNetworkError: error.isNetworkError || false,
      isAuthError: error.isAuthError || false,
    };
  }
}

/**
 * Get error message utility (for components)
 * ALWAYS returns a string, never an object
 */
export function getErrorMessage(error, fallback = 'Something went wrong. Please try again.') {
  if (!error) return fallback;
  
  // Already normalized error (from interceptor)
  if (typeof error.message === 'string') {
    return error.message;
  }
  
  // String error
  if (typeof error === 'string') return error;
  
  // Raw axios error (shouldn't happen if interceptor works, but safety check)
  if (error.response?.data) {
    return extractErrorMessage(error.response.data, fallback);
  }
  
  return fallback;
}

/**
 * Check if error is a network/server unavailable error
 */
export function isServerUnavailable(error) {
  return error?.isNetworkError === true || error?.error_code === 'E_NET' || error?.error_code === 'E_SERVER';
}

// Export the configured instance
export default http;

// Export base URLs for reference
export const API_URL = API_BASE_URL;
export const API_V1 = `${API_BASE_URL}/api/v1`;

/**
 * AuthContext - SINGLE SOURCE OF TRUTH FOR AUTH STATE
 * 
 * Rules:
 * - Uses ONLY localStorage["token"] for token storage
 * - Uses ONLY src/api/http.js for API calls
 * - Exposes: login(), logout(), isAuthenticated, user, role, serverUnavailable
 * - On network failure during validation, sets serverUnavailable flag (does NOT logout)
 * - On auth failure (401), clears token
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import http, { getErrorMessage, isServerUnavailable } from '../api/http';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [serverUnavailable, setServerUnavailable] = useState(false);
  
  // Ref to prevent race conditions during auth initialization
  const isInitializing = React.useRef(false);

  // Get token from localStorage
  const getToken = useCallback(() => localStorage.getItem('token'), []);

  // Validate token on app load
  useEffect(() => {
    const initAuth = async () => {
      // Prevent multiple simultaneous initializations
      if (isInitializing.current) {
        return;
      }
      isInitializing.current = true;
      
      const storedToken = getToken();
      
      if (!storedToken) {
        setLoading(false);
        isInitializing.current = false;
        return;
      }

      try {
        const response = await http.post('/auth/validate-token');
        
        if (response.data.valid && response.data.user) {
          setUser(response.data.user);
          setServerUnavailable(false);
          // Update stored user data
          localStorage.setItem('user', JSON.stringify(response.data.user));
        } else {
          // Invalid token - clear it
          localStorage.removeItem('token');
          setUser(null);
        }
      } catch (error) {
        if (isServerUnavailable(error)) {
          // Server is down - keep token, set flag
          console.warn('Server unavailable during token validation');
          setServerUnavailable(true);
          // Try to restore user from localStorage if available
          const storedUser = localStorage.getItem('user');
          if (storedUser) {
            try {
              setUser(JSON.parse(storedUser));
            } catch (e) {
              // Invalid JSON, ignore
            }
          }
        } else if (error.isAuthError) {
          // Auth error (401) - token is invalid, clear it
          localStorage.removeItem('token');
          localStorage.removeItem('user');
          setUser(null);
        } else {
          // Other error (4xx, transient failures) - DON'T clear token
          // Keep user logged in, they can retry. Only 401 should force logout.
          console.warn('Token validation failed (non-auth error), keeping session:', error.message);
          // Try to restore user from localStorage
          const storedUser = localStorage.getItem('user');
          if (storedUser) {
            try {
              setUser(JSON.parse(storedUser));
            } catch (e) {
              // Invalid JSON - can't restore, but don't clear token
              console.warn('Could not restore user from localStorage');
            }
          }
        }
      } finally {
        setLoading(false);
        isInitializing.current = false;
      }
    };

    initAuth();
  }, [getToken]);

  /**
   * Login with username and password
   */
  const login = async (username, password) => {
    try {
      const response = await http.post('/auth/login', { username, password });
      
      if (!response.data.success) {
        throw new Error(response.data.message || 'Login failed');
      }
      
      const { access_token, user: userData } = response.data;
      
      // Store token and user
      localStorage.setItem('token', access_token);
      localStorage.setItem('user', JSON.stringify(userData));
      
      setUser(userData);
      setServerUnavailable(false);
      
      return { success: true, user: userData };
    } catch (error) {
      const message = getErrorMessage(error, 'Login failed');
      const isNetwork = isServerUnavailable(error);
      
      if (isNetwork) {
        setServerUnavailable(true);
      }
      
      return { 
        success: false, 
        message,
        isNetworkError: isNetwork,
      };
    }
  };

  /**
   * Register new user
   */
  const register = async (username, password, displayName, referralCode) => {
    try {
      const response = await http.post('/auth/signup', {
        username,
        password,
        display_name: displayName,
        referred_by_code: referralCode || null,
      });
      
      if (!response.data.success) {
        throw new Error(response.data.message || 'Registration failed');
      }
      
      // Auto-login after registration
      return await login(username, password);
    } catch (error) {
      const message = getErrorMessage(error, 'Registration failed');
      return { 
        success: false, 
        message,
        isNetworkError: isServerUnavailable(error),
      };
    }
  };

  /**
   * Validate a portal magic-link token
   * Used by /p/:token route
   */
  const validatePortalToken = async (token) => {
    try {
      const response = await http.post('/auth/validate-token', {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (response.data.valid && response.data.user) {
        // Store token and user
        localStorage.setItem('token', token);
        localStorage.setItem('user', JSON.stringify(response.data.user));
        
        setUser(response.data.user);
        setServerUnavailable(false);
        
        return { success: true, user: response.data.user };
      }
      
      return { success: false, message: 'Invalid or expired token' };
    } catch (error) {
      const message = getErrorMessage(error, 'Token validation failed');
      const isNetwork = isServerUnavailable(error);
      
      if (isNetwork) {
        setServerUnavailable(true);
      }
      
      return { 
        success: false, 
        message,
        isNetworkError: isNetwork,
      };
    }
  };

  /**
   * Logout - clear all auth state
   */
  const logout = useCallback(() => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setUser(null);
  }, []);

  /**
   * Clear server unavailable flag (for retry)
   */
  const clearServerError = useCallback(() => {
    setServerUnavailable(false);
  }, []);

  const value = {
    // State
    user,
    loading,
    serverUnavailable,
    
    // Computed
    isAuthenticated: !!user,
    role: user?.role || null,
    isAdmin: user?.role === 'admin',
    isClient: user?.role === 'client' || (user && user.role !== 'admin'),
    
    // Actions
    login,
    register,
    logout,
    validatePortalToken,
    clearServerError,
    getToken,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext;

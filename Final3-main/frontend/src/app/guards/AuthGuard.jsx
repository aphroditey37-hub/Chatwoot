/**
 * Route Guards - SINGLE SOURCE OF TRUTH
 * 
 * GuestGuard: For login/register pages - redirects if authenticated
 * ClientGuard: For /client/* routes - requires authentication
 * AdminGuard: For /admin/* routes - requires admin role
 */

import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

/**
 * Loading Spinner Component
 */
const LoadingSpinner = () => (
  <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center">
    <div className="w-8 h-8 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
  </div>
);

/**
 * GuestGuard - For login/register pages
 * - If authenticated admin -> /admin
 * - If authenticated client -> /client/home
 * - Else allow access
 */
export const GuestGuard = ({ children }) => {
  const { isAuthenticated, isAdmin, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return <LoadingSpinner />;
  }

  if (isAuthenticated) {
    // Get intended redirect from state, or use defaults
    const from = location.state?.from?.pathname;
    
    if (from && !from.includes('/login')) {
      return <Navigate to={from} replace />;
    }
    
    if (isAdmin) {
      return <Navigate to="/admin" replace />;
    }
    
    return <Navigate to="/client/home" replace />;
  }

  return children;
};

/**
 * ClientGuard - For /client/* routes
 * - If not authenticated -> /login
 * - If admin -> /admin
 * - Else allow access
 */
export const ClientGuard = ({ children }) => {
  const { isAuthenticated, isAdmin, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return <LoadingSpinner />;
  }

  if (!isAuthenticated) {
    // Redirect to login, save intended destination
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (isAdmin) {
    // Admins should use admin panel
    return <Navigate to="/admin" replace />;
  }

  return children;
};

/**
 * AdminGuard - For /admin/* routes
 * - If not authenticated -> /admin/login
 * - If not admin -> /login
 * - Else allow access
 */
export const AdminGuard = ({ children }) => {
  const { isAuthenticated, isAdmin, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return <LoadingSpinner />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/admin/login" state={{ from: location }} replace />;
  }

  if (!isAdmin) {
    // Non-admins go to client area
    return <Navigate to="/login" replace />;
  }

  return children;
};

export default { GuestGuard, ClientGuard, AdminGuard };

/**
 * PublicRoutes - Routes accessible without authentication
 */

import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { GuestGuard } from '../guards';
import { ROUTES } from './constants';

// Lazy load public pages
const Login = React.lazy(() => import('../../pages/Login'));
const Register = React.lazy(() => import('../../pages/Register'));
const AdminLogin = React.lazy(() => import('../../pages/AdminLogin'));
const PublicGames = React.lazy(() => import('../../pages/PublicGamesNew'));

// Loading fallback
const PageFallback = () => (
  <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center">
    <div className="w-8 h-8 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
  </div>
);

export const PublicRoutes = () => {
  return (
    <React.Suspense fallback={<PageFallback />}>
      <Routes>
        {/* Public Games - No auth required */}
        <Route path={ROUTES.PUBLIC.GAMES} element={<PublicGames />} />
        
        {/* Auth pages - Redirect if already logged in */}
        <Route 
          path={ROUTES.PUBLIC.LOGIN} 
          element={
            <GuestGuard redirectTo={ROUTES.CLIENT.HOME}>
              <Login />
            </GuestGuard>
          } 
        />
        <Route 
          path={ROUTES.PUBLIC.REGISTER} 
          element={
            <GuestGuard redirectTo={ROUTES.CLIENT.HOME}>
              <Register />
            </GuestGuard>
          } 
        />
        <Route 
          path={ROUTES.PUBLIC.ADMIN_LOGIN} 
          element={
            <GuestGuard redirectTo={ROUTES.ADMIN.DASHBOARD}>
              <AdminLogin />
            </GuestGuard>
          } 
        />

        {/* Default redirect */}
        <Route path="/" element={<Navigate to={ROUTES.PUBLIC.GAMES} replace />} />
      </Routes>
    </React.Suspense>
  );
};

export default PublicRoutes;

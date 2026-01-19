/**
 * ClientRoutes - Protected routes for authenticated clients
 */

import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { ClientGuard } from '../guards';

// Lazy load client pages
const ClientHome = React.lazy(() => import('../../pages/client/ClientHome'));
const ClientWallet = React.lazy(() => import('../../pages/client/ClientWallet'));
const ClientGames = React.lazy(() => import('../../pages/client/ClientGames'));
const ClientProfile = React.lazy(() => import('../../pages/client/ClientProfile'));
const ClientReferrals = React.lazy(() => import('../../pages/client/ClientReferrals'));
const ClientRewards = React.lazy(() => import('../../pages/client/ClientRewards'));
const AddFunds = React.lazy(() => import('../../pages/client/AddFunds'));
const Withdraw = React.lazy(() => import('../../pages/client/Withdraw'));
const TransactionDetail = React.lazy(() => import('../../pages/client/TransactionDetail'));

// Portal pages (only PortalLanding kept for magic link)
const PortalLanding = React.lazy(() => import('../../pages/portal/PortalLanding'));

// Loading fallback
const PageFallback = () => (
  <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center">
    <div className="w-8 h-8 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
  </div>
);

/**
 * Wrapper component that applies ClientGuard to all client routes
 */
const ProtectedRoute = ({ children }) => (
  <ClientGuard>{children}</ClientGuard>
);

export const ClientRoutes = () => {
  return (
    <React.Suspense fallback={<PageFallback />}>
      <Routes>
        {/* ==================== CLIENT ROUTES ==================== */}
        <Route path="/client/home" element={<ProtectedRoute><ClientHome /></ProtectedRoute>} />
        <Route path="/client/wallet" element={<ProtectedRoute><ClientWallet /></ProtectedRoute>} />
        <Route path="/client/wallet/add" element={<ProtectedRoute><AddFunds /></ProtectedRoute>} />
        <Route path="/client/wallet/withdraw" element={<ProtectedRoute><Withdraw /></ProtectedRoute>} />
        <Route path="/client/wallet/transaction/:orderId" element={<ProtectedRoute><TransactionDetail /></ProtectedRoute>} />
        <Route path="/client/games" element={<ProtectedRoute><ClientGames /></ProtectedRoute>} />
        <Route path="/client/referrals" element={<ProtectedRoute><ClientReferrals /></ProtectedRoute>} />
        <Route path="/client/rewards" element={<ProtectedRoute><ClientRewards /></ProtectedRoute>} />
        <Route path="/client/profile" element={<ProtectedRoute><ClientProfile /></ProtectedRoute>} />

        {/* ==================== LEGACY PORTAL REDIRECTS ==================== */}
        <Route path="/portal" element={<Navigate to="/client/home" replace />} />
        <Route path="/portal/transactions" element={<Navigate to="/client/wallet" replace />} />
        <Route path="/portal/credentials" element={<Navigate to="/client/games" replace />} />
        <Route path="/portal/referrals" element={<Navigate to="/client/referrals" replace />} />
        <Route path="/portal/withdrawals" element={<Navigate to="/client/wallet" replace />} />
        <Route path="/portal/wallet" element={<Navigate to="/client/wallet" replace />} />
        <Route path="/portal/wallets" element={<Navigate to="/client/wallet" replace />} />
        <Route path="/portal/rewards" element={<Navigate to="/client/rewards" replace />} />
        <Route path="/portal/load-game" element={<Navigate to="/client/games" replace />} />
        <Route path="/portal/security" element={<Navigate to="/client/profile" replace />} />
        <Route path="/portal/bonus-tasks" element={<Navigate to="/client/rewards" replace />} />

        {/* ==================== SPECIAL ROUTES ==================== */}
        {/* Magic Link Landing */}
        <Route path="/p/:token" element={<PortalLanding />} />
        
        {/* Client Login Redirect */}
        <Route path="/client-login" element={<Navigate to="/login" replace />} />
      </Routes>
    </React.Suspense>
  );
};

export default ClientRoutes;

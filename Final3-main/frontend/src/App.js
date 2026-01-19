/**
 * App.js - SINGLE SOURCE OF TRUTH FOR ROUTING
 * 
 * NO DUPLICATE ROUTERS - This is the only App.js
 * Uses: ClientGuard (never PortalRoute) for /client/* routes
 */

import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import './App.css';

// Guards - SINGLE SOURCE
import { GuestGuard, ClientGuard, AdminGuard } from './app/guards/AuthGuard';

// Layouts
import AdminLayout from './components/AdminLayout';

// ================== PUBLIC PAGES ==================
import Login from './pages/Login';
import AdminLogin from './pages/AdminLogin';
import Register from './pages/Register';
import PublicGamesNew from './pages/PublicGamesNew';

// ================== CLIENT PAGES (Mobile-First) ==================
import ClientHome from './pages/client/ClientHome';
import ClientWallet from './pages/client/ClientWallet';
import ClientGames from './pages/client/ClientGames';
import ClientProfile from './pages/client/ClientProfile';
import AddFunds from './pages/client/AddFunds';
import Withdraw from './pages/client/Withdraw';
import TransactionDetail from './pages/client/TransactionDetail';
import ClientReferrals from './pages/client/ClientReferrals';
import ClientRewards from './pages/client/ClientRewards';

// ================== PORTAL COMPAT (Magic Link) ==================
import PortalLanding from './pages/portal/PortalLanding';

// ================== ADMIN PAGES ==================
import AdminDashboard from './pages/admin/AdminDashboard';
import AdminApprovals from './pages/admin/AdminApprovals';
import AdminOrders from './pages/admin/AdminOrders';
import AdminClients from './pages/admin/AdminClients';
import AdminClientDetail from './pages/admin/AdminClientDetail';
import AdminClientCreate from './pages/admin/AdminClientCreate';
import AdminGames from './pages/admin/AdminGames';
import AdminRulesEngine from './pages/admin/AdminRulesEngine';
import AdminReferrals from './pages/admin/AdminReferrals';
import AdminPromoCodes from './pages/admin/AdminPromoCodes';
import AdminPromoDetail from './pages/admin/AdminPromoDetail';
import AdminReports from './pages/admin/AdminReports';
import AdminSystem from './pages/admin/AdminSystem';
import AdminAuditLogs from './pages/admin/AdminAuditLogs';
import AdminBalanceControl from './pages/admin/AdminBalanceControl';
import AdminSettings from './pages/admin/AdminSettings';
import AdminPaymentPanel from './pages/admin/AdminPaymentPanel';
import AdminPerksPage from './pages/admin/AdminPerksPage';
import AdminOperationsPanel from './pages/admin/AdminOperationsPanel';

// Admin System Subsections
import SystemWebhooks from './pages/admin/system/SystemWebhooks';
import SystemAPIAccess from './pages/admin/system/SystemAPIAccess';
import SystemDocumentation from './pages/admin/system/SystemDocumentation';
import AdminRewardsPage from './pages/admin/system/AdminRewards';
import AdminPaymentQR from './pages/admin/system/AdminPaymentQR';
import AdminWalletLoads from './pages/admin/system/AdminWalletLoads';
import TelegramBots from './pages/admin/system/TelegramBots';

/**
 * PortalRedirect - Smart redirect for legacy /portal routes
 */
const PortalRedirect = () => {
  const token = localStorage.getItem('token');
  if (token) {
    return <Navigate to="/client/home" replace />;
  }
  return <Navigate to="/login" replace />;
};

function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="min-h-screen bg-black">
          <Routes>
            {/* ==================== PUBLIC ROUTES ==================== */}
            <Route path="/games" element={<PublicGamesNew />} />
            
            <Route path="/login" element={
              <GuestGuard><Login /></GuestGuard>
            } />
            
            <Route path="/register" element={
              <GuestGuard><Register /></GuestGuard>
            } />
            
            <Route path="/admin/login" element={
              <GuestGuard><AdminLogin /></GuestGuard>
            } />

            {/* ==================== CLIENT ROUTES (ClientGuard - NOT PortalRoute) ==================== */}
            <Route path="/client/home" element={
              <ClientGuard><ClientHome /></ClientGuard>
            } />
            
            <Route path="/client/wallet" element={
              <ClientGuard><ClientWallet /></ClientGuard>
            } />
            
            <Route path="/client/wallet/add" element={
              <ClientGuard><AddFunds /></ClientGuard>
            } />
            
            <Route path="/client/wallet/withdraw" element={
              <ClientGuard><Withdraw /></ClientGuard>
            } />
            
            <Route path="/client/wallet/transaction/:orderId" element={
              <ClientGuard><TransactionDetail /></ClientGuard>
            } />
            
            <Route path="/client/games" element={
              <ClientGuard><ClientGames /></ClientGuard>
            } />
            
            <Route path="/client/referrals" element={
              <ClientGuard><ClientReferrals /></ClientGuard>
            } />
            
            <Route path="/client/rewards" element={
              <ClientGuard><ClientRewards /></ClientGuard>
            } />
            
            <Route path="/client/profile" element={
              <ClientGuard><ClientProfile /></ClientGuard>
            } />

            {/* ==================== PORTAL COMPATIBILITY ==================== */}
            {/* Magic Link Landing - REQUIRED */}
            <Route path="/p/:token" element={<PortalLanding />} />
            
            {/* /client-login -> /login */}
            <Route path="/client-login" element={<Navigate to="/login" replace />} />
            
            {/* /portal/* -> redirect based on auth */}
            <Route path="/portal" element={<PortalRedirect />} />
            <Route path="/portal/*" element={<PortalRedirect />} />

            {/* ==================== ADMIN ROUTES ==================== */}
            <Route path="/admin" element={
              <AdminGuard><AdminLayout /></AdminGuard>
            }>
              <Route index element={<AdminDashboard />} />
              <Route path="approvals" element={<AdminApprovals />} />
              <Route path="orders" element={<AdminOrders />} />
              <Route path="clients" element={<AdminClients />} />
              <Route path="clients/new" element={<AdminClientCreate />} />
              <Route path="clients/:clientId" element={<AdminClientDetail />} />
              <Route path="games" element={<AdminGames />} />
              <Route path="rules" element={<AdminRulesEngine />} />
              <Route path="referrals" element={<AdminReferrals />} />
              <Route path="promo-codes" element={<AdminPromoCodes />} />
              <Route path="promo-codes/:codeId" element={<AdminPromoDetail />} />
              <Route path="balance-control" element={<AdminBalanceControl />} />
              <Route path="reports" element={<AdminReports />} />
              <Route path="system" element={<AdminSystem />} />
              <Route path="system/webhooks" element={<SystemWebhooks />} />
              <Route path="system/api-access" element={<SystemAPIAccess />} />
              <Route path="system/documentation" element={<SystemDocumentation />} />
              <Route path="system/rewards" element={<AdminRewardsPage />} />
              <Route path="system/automations" element={<AdminOperationsPanel />} />
              <Route path="system/payment-methods" element={<AdminPaymentPanel />} />
              <Route path="system/telegram" element={<TelegramBots />} />
              <Route path="system/telegram-bots" element={<TelegramBots />} />
              <Route path="system/payment-qr" element={<AdminPaymentQR />} />
              <Route path="system/wallet-loads" element={<AdminWalletLoads />} />
              <Route path="audit-logs" element={<AdminAuditLogs />} />
              {/* Legacy routes */}
              <Route path="operations" element={<AdminOperationsPanel />} />
              <Route path="payment-panel" element={<AdminPaymentPanel />} />
              <Route path="telegram" element={<TelegramBots />} />
              <Route path="settings" element={<AdminSettings />} />
            </Route>
            
            <Route path="/admin/perks" element={
              <AdminGuard><AdminPerksPage /></AdminGuard>
            } />

            {/* ==================== DEFAULT ROUTES ==================== */}
            <Route path="/" element={<Navigate to="/games" replace />} />
            <Route path="*" element={<Navigate to="/games" replace />} />
          </Routes>
        </div>
      </Router>
    </AuthProvider>
  );
}

export default App;

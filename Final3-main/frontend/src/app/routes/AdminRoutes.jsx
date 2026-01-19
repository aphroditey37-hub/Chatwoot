/**
 * AdminRoutes - Protected routes for admin users only
 */

import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { AdminGuard } from '../guards';
import AdminLayout from '../../components/AdminLayout';

// Lazy load admin pages
const AdminDashboard = React.lazy(() => import('../../pages/admin/AdminDashboard'));
const AdminApprovals = React.lazy(() => import('../../pages/admin/AdminApprovals'));
const AdminOrders = React.lazy(() => import('../../pages/admin/AdminOrders'));
const AdminClients = React.lazy(() => import('../../pages/admin/AdminClients'));
const AdminClientDetail = React.lazy(() => import('../../pages/admin/AdminClientDetail'));
const AdminClientCreate = React.lazy(() => import('../../pages/admin/AdminClientCreate'));
const AdminGames = React.lazy(() => import('../../pages/admin/AdminGames'));
const AdminRulesEngine = React.lazy(() => import('../../pages/admin/AdminRulesEngine'));
const AdminReferrals = React.lazy(() => import('../../pages/admin/AdminReferrals'));
const AdminPromoCodes = React.lazy(() => import('../../pages/admin/AdminPromoCodes'));
const AdminPromoDetail = React.lazy(() => import('../../pages/admin/AdminPromoDetail'));
const AdminReports = React.lazy(() => import('../../pages/admin/AdminReports'));
const AdminSystem = React.lazy(() => import('../../pages/admin/AdminSystem'));
const AdminAuditLogs = React.lazy(() => import('../../pages/admin/AdminAuditLogs'));
const AdminBalanceControl = React.lazy(() => import('../../pages/admin/AdminBalanceControl'));

// System subsections
const SystemWebhooks = React.lazy(() => import('../../pages/admin/system/SystemWebhooks'));
const SystemAPIAccess = React.lazy(() => import('../../pages/admin/system/SystemAPIAccess'));
const SystemDocumentation = React.lazy(() => import('../../pages/admin/system/SystemDocumentation'));
const AdminRewardsPage = React.lazy(() => import('../../pages/admin/system/AdminRewards'));
const AdminPaymentQR = React.lazy(() => import('../../pages/admin/system/AdminPaymentQR'));
const AdminWalletLoads = React.lazy(() => import('../../pages/admin/system/AdminWalletLoads'));
const TelegramBots = React.lazy(() => import('../../pages/admin/system/TelegramBots'));

// Legacy pages
const AdminSettings = React.lazy(() => import('../../pages/admin/AdminSettings'));
const AdminPaymentPanel = React.lazy(() => import('../../pages/admin/AdminPaymentPanel'));
const AdminOperationsPanel = React.lazy(() => import('../../pages/admin/AdminOperationsPanel'));
const AdminPerksPage = React.lazy(() => import('../../pages/admin/AdminPerksPage'));
const AdminPromotions = React.lazy(() => import('../../pages/admin/AdminPromotions'));

// AI Test Spot (feature-flagged)
const AdminAITestSpot = React.lazy(() => import('../../pages/admin/AdminAITestSpot'));

// Feature flag for AI Test Spot - only enabled in development
const ENABLE_AI_TEST_SPOT = process.env.REACT_APP_ENABLE_ADMIN_TEST_SPOT === 'true';

// Loading fallback
const PageFallback = () => (
  <div className="min-h-screen bg-gray-900 flex items-center justify-center">
    <div className="w-8 h-8 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
  </div>
);

export const AdminRoutes = () => {
  return (
    <React.Suspense fallback={<PageFallback />}>
      <Routes>
        {/* Admin Layout with Sidebar */}
        <Route
          path="/admin"
          element={
            <AdminGuard>
              <AdminLayout />
            </AdminGuard>
          }
        >
          {/* Dashboard */}
          <Route index element={<AdminDashboard />} />
          
          {/* Core Management */}
          <Route path="approvals" element={<AdminApprovals />} />
          <Route path="orders" element={<AdminOrders />} />
          
          {/* Client Management */}
          <Route path="clients" element={<AdminClients />} />
          <Route path="clients/new" element={<AdminClientCreate />} />
          <Route path="clients/:clientId" element={<AdminClientDetail />} />
          
          {/* Game Management */}
          <Route path="games" element={<AdminGames />} />
          
          {/* Rules & Configuration */}
          <Route path="rules" element={<AdminRulesEngine />} />
          
          {/* Referrals & Promos */}
          <Route path="referrals" element={<AdminReferrals />} />
          <Route path="promo-codes" element={<AdminPromoCodes />} />
          <Route path="promo-codes/:codeId" element={<AdminPromoDetail />} />
          <Route path="promotions" element={<AdminPromotions />} />
          
          {/* Balance Control */}
          <Route path="balance-control" element={<AdminBalanceControl />} />
          
          {/* Reports */}
          <Route path="reports" element={<AdminReports />} />
          
          {/* System Configuration */}
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
          
          {/* Audit & Logs */}
          <Route path="audit-logs" element={<AdminAuditLogs />} />
          
          {/* AI Test Spot (feature-flagged) */}
          {ENABLE_AI_TEST_SPOT && (
            <Route path="ai-test" element={<AdminAITestSpot />} />
          )}
          
          {/* Legacy Routes (backwards compatibility) */}
          <Route path="operations" element={<AdminOperationsPanel />} />
          <Route path="payment-panel" element={<AdminPaymentPanel />} />
          <Route path="telegram" element={<TelegramBots />} />
          <Route path="settings" element={<AdminSettings />} />
          <Route path="perks" element={<AdminPerksPage />} />
        </Route>
      </Routes>
    </React.Suspense>
  );
};

export default AdminRoutes;

/**
 * Admin API Client - Centralized API for Admin Operations
 * 
 * All admin API calls MUST go through this module.
 * Uses the same http client as client-side for consistency.
 */

import http, { getErrorMessage } from './http';

// Re-export utilities
export { getErrorMessage };

// ============================================
// DASHBOARD & STATS
// ============================================
export const dashboardApi = {
  getStats: () => 
    http.get('/admin/stats'),
  
  getDashboard: () =>
    http.get('/admin/dashboard'),
};

// ============================================
// USER MANAGEMENT
// ============================================
export const usersApi = {
  getAll: (params = {}) => {
    const query = new URLSearchParams();
    if (params.page) query.append('page', params.page);
    if (params.limit) query.append('limit', params.limit);
    if (params.search) query.append('search', params.search);
    if (params.status) query.append('status', params.status);
    const queryStr = query.toString();
    return http.get(`/admin/clients${queryStr ? '?' + queryStr : ''}`);
  },
  
  getById: (userId) => 
    http.get(`/admin/clients/${userId}`),
  
  create: (data) =>
    http.post('/admin/clients', data),
  
  update: (userId, data) =>
    http.put(`/admin/clients/${userId}`, data),
  
  // Status updates use PUT /admin/clients/{userId} with status field
  // Backend accepts: status: 'active' | true | 'true' for active, anything else for inactive
  updateStatus: (userId, status, reason = '') =>
    http.put(`/admin/clients/${userId}`, { status, reason }),
  
  // NOTE: For bonus adjustments, use balanceControlApi.load() instead
  
  suspend: (userId, reason) =>
    http.put(`/admin/clients/${userId}`, { status: 'suspended', is_locked: true, reason }),
  
  ban: (userId, reason) =>
    http.put(`/admin/clients/${userId}`, { status: 'banned', is_locked: true, reason }),
  
  activate: (userId) =>
    http.put(`/admin/clients/${userId}`, { status: 'active', is_locked: false }),
  
  // Overrides
  getOverrides: (userId) =>
    http.get(`/admin/clients/${userId}/overrides`),
  
  updateOverrides: (userId, overrides) =>
    http.put(`/admin/clients/${userId}/overrides`, overrides),
  
  // Activity
  getActivity: (userId) =>
    http.get(`/admin/clients/${userId}/activity`),
  
  // Credentials
  getCredentials: (userId) =>
    http.get(`/admin/clients/${userId}/credentials`),
  
  assignCredential: (userId, credential) =>
    http.post(`/admin/clients/${userId}/credentials`, credential),
};

// ============================================
// ANALYTICS
// ============================================
export const analyticsApi = {
  getClientAnalytics: (userId) =>
    http.get(`/admin/analytics/client/${userId}`),
  
  getGameAnalytics: (gameName) =>
    http.get(`/admin/analytics/game/${gameName}`),
  
  getRiskSnapshot: () =>
    http.get('/admin/analytics/risk-snapshot'),
  
  getRiskExposure: () =>
    http.get('/admin/analytics/risk-exposure'),
  
  getPlatformTrends: (params = {}) => {
    const query = new URLSearchParams();
    query.append('days', params.days || 7);
    if (params.game && params.game !== 'all') {
      query.append('game', params.game);
    }
    if (params.client_segment && params.client_segment !== 'all') {
      query.append('client_segment', params.client_segment);
    }
    return http.get(`/admin/analytics/platform-trends?${query.toString()}`);
  },
  
  getAdvancedMetrics: () =>
    http.get('/admin/analytics/advanced-metrics'),
};

// ============================================
// ORDERS & TRANSACTIONS
// ============================================
export const ordersApi = {
  getAll: (params = {}) => {
    const query = new URLSearchParams();
    const limit = params.limit || 50;
    
    // Backend expects: status_filter, order_type, limit, offset
    if (limit) query.append('limit', limit);
    if (params.status_filter) query.append('status_filter', params.status_filter);
    if (params.order_type) query.append('order_type', params.order_type);
    
    // Convert page to offset: offset = (page - 1) * limit
    if (params.page && params.page > 1) {
      const offset = (params.page - 1) * limit;
      query.append('offset', offset);
    }
    
    // Support search if backend has it
    if (params.search) query.append('search', params.search);
    
    const queryStr = query.toString();
    return http.get(`/admin/orders${queryStr ? '?' + queryStr : ''}`);
  },
  
  getById: (orderId) =>
    http.get(`/admin/orders/${orderId}`),
  
  approve: (orderId, notes = '') =>
    http.post(`/admin/approvals/${orderId}/action`, { action: 'approve', reason: notes }),
  
  reject: (orderId, reason) =>
    http.post(`/admin/approvals/${orderId}/action`, { action: 'reject', reason }),
};

// ============================================
// APPROVALS (Unified - uses /admin/approvals/{order_id}/action)
// ============================================
export const approvalsApi = {
  // Get all pending items (optionally filtered by order_type)
  getPending: (orderType = null) => {
    const query = orderType ? `?order_type=${orderType}` : '';
    return http.get(`/admin/approvals/pending${query}`);
  },
  
  // Perform action on any order (approve/reject)
  // This is the ONLY action endpoint - backend uses /admin/approvals/{order_id}/action
  performAction: (orderId, action, reason = '') =>
    http.post(`/admin/approvals/${orderId}/action`, { action, reason: reason || undefined }),
  
  // Convenience methods - all route to the same unified endpoint
  approve: (orderId, notes = '') =>
    http.post(`/admin/approvals/${orderId}/action`, { action: 'approve', reason: notes || undefined }),
  
  reject: (orderId, reason) =>
    http.post(`/admin/approvals/${orderId}/action`, { action: 'reject', reason }),
  
  // Wallet Loads - use getPending with filter + performAction
  getPendingLoads: () =>
    http.get('/admin/approvals/pending?order_type=deposit'),
  
  approveLoad: (requestId, notes = '') =>
    http.post(`/admin/approvals/${requestId}/action`, { action: 'approve', reason: notes || undefined }),
  
  rejectLoad: (requestId, reason) =>
    http.post(`/admin/approvals/${requestId}/action`, { action: 'reject', reason }),
  
  // Withdrawals - use getPending with filter + performAction
  getPendingWithdrawals: () =>
    http.get('/admin/approvals/pending?order_type=withdrawal'),
  
  approveWithdrawal: (orderId, notes = '') =>
    http.post(`/admin/approvals/${orderId}/action`, { action: 'approve', reason: notes || undefined }),
  
  rejectWithdrawal: (orderId, reason) =>
    http.post(`/admin/approvals/${orderId}/action`, { action: 'reject', reason }),
  
  // Game Loads - use getPending with filter + performAction
  getPendingGameLoads: () =>
    http.get('/admin/approvals/pending?order_type=game_load'),
  
  approveGameLoad: (orderId) =>
    http.post(`/admin/approvals/${orderId}/action`, { action: 'approve' }),
  
  rejectGameLoad: (orderId, reason) =>
    http.post(`/admin/approvals/${orderId}/action`, { action: 'reject', reason }),
  
  // Redemptions - use getPending with filter + performAction
  getPendingRedemptions: () =>
    http.get('/admin/approvals/pending?order_type=redemption'),
  
  approveRedemption: (orderId) =>
    http.post(`/admin/approvals/${orderId}/action`, { action: 'approve' }),
  
  rejectRedemption: (orderId, reason) =>
    http.post(`/admin/approvals/${orderId}/action`, { action: 'reject', reason }),
};

// ============================================
// SYSTEM MANAGEMENT
// ============================================
export const systemApi = {
  // Wallet Loads
  getWalletLoads: (params = {}) => {
    const query = new URLSearchParams();
    if (params.status) query.append('status', params.status);
    if (params.limit) query.append('limit', params.limit);
    const queryStr = query.toString();
    return http.get(`/admin/system/wallet-loads${queryStr ? '?' + queryStr : ''}`);
  },
  
  getWalletLoadById: (requestId) =>
    http.get(`/admin/system/wallet-loads/${requestId}`),
  
  // Payment Methods
  getPaymentMethods: () =>
    http.get('/admin/system/payment-methods'),
  
  createPaymentMethod: (data) =>
    http.post('/admin/system/payment-methods', data),
  
  updatePaymentMethod: (methodId, data) =>
    http.put(`/admin/system/payment-methods/${methodId}`, data),
  
  deletePaymentMethod: (methodId) =>
    http.delete(`/admin/system/payment-methods/${methodId}`),
  
  // Payment QR
  getPaymentQr: () =>
    http.get('/admin/system/payment-qr'),
  
  createPaymentQr: (data) =>
    http.post('/admin/system/payment-qr', data),
  
  updatePaymentQr: (qrId, data) =>
    http.patch(`/admin/system/payment-qr/${qrId}`, data),
  
  deletePaymentQr: (qrId) =>
    http.delete(`/admin/system/payment-qr/${qrId}`),
  
  // API Keys
  getApiKeys: () =>
    http.get('/admin/system/api-keys'),
  
  createApiKey: (data) =>
    http.post('/admin/system/api-keys', data),
  
  deleteApiKey: (keyId) =>
    http.delete(`/admin/system/api-keys/${keyId}`),
  
  // Webhooks
  getWebhooks: () =>
    http.get('/admin/system/webhooks'),
  
  createWebhook: (data) =>
    http.post('/admin/system/webhooks', data),
  
  updateWebhook: (webhookId, data) =>
    http.put(`/admin/system/webhooks/${webhookId}`, data),
  
  deleteWebhook: (webhookId) =>
    http.delete(`/admin/system/webhooks/${webhookId}`),
  
  getWebhookDeliveries: (webhookId, limit = 50) =>
    http.get(`/admin/system/webhooks/${webhookId}/deliveries?limit=${limit}`),
};

// ============================================
// SETTINGS (read-only - use /admin/system/settings)
// ============================================
export const settingsApi = {
  // Backend only supports GET /admin/system/settings
  get: () =>
    http.get('/admin/system/settings'),
  
  // NOTE: Update operations route through rules/system endpoints
  // These methods are kept for API compatibility but route to correct endpoints
  update: (settings) =>
    http.put('/admin/rules', settings),
  
  updateReferralTiers: (tiers) =>
    http.put('/admin/rules', { referral_tiers: tiers }),
  
  removeTier: (tierNumber) =>
    http.put('/admin/rules', { remove_tier: tierNumber }),
  
  updateBonusMilestones: (milestones) =>
    http.put('/admin/rules', { bonus_milestones: milestones }),
  
  updateAntiFraud: (updates) =>
    http.put('/admin/rules', { anti_fraud: updates }),
  
  // Reset defaults - NOT SUPPORTED by backend, returns error
  resetDefaults: (section) => {
    console.warn('resetDefaults is not supported by backend');
    return Promise.reject(new Error('Reset defaults is not available'));
  },
};

// ============================================
// GAMES & RULES
// ============================================
export const gamesApi = {
  getAll: () =>
    http.get('/admin/games'),
  
  update: (gameId, data) =>
    http.put(`/admin/games/${gameId}`, data),
  
  getRules: () =>
    http.get('/admin/rules'),
  
  createRule: (data) =>
    http.post('/admin/rules', data),
  
  // NOTE: Rules are read-only in backend v2, no delete endpoint available
};

// ============================================
// REFERRAL PERKS - NOT AVAILABLE IN BACKEND v2
// ============================================
// NOTE: Perks endpoints exist in admin_routes.py but NOT in admin_routes_v2.py
// These methods will return errors - use rewards API instead for similar functionality
export const perksApi = {
  getAll: () => {
    console.warn('perksApi.getAll: endpoint not available in backend v2');
    return Promise.reject(new Error('Perks endpoint not available'));
  },
  
  create: (data) => {
    console.warn('perksApi.create: endpoint not available in backend v2');
    return Promise.reject(new Error('Perks endpoint not available'));
  },
  
  update: (perkId, data) => {
    console.warn('perksApi.update: endpoint not available in backend v2');
    return Promise.reject(new Error('Perks endpoint not available'));
  },
  
  delete: (perkId) => {
    console.warn('perksApi.delete: endpoint not available in backend v2');
    return Promise.reject(new Error('Perks endpoint not available'));
  },
};

// ============================================
// PROMO CODES
// ============================================
export const promoCodesApi = {
  getAll: (params = {}) => {
    const query = new URLSearchParams();
    if (params.status) query.append('status', params.status);
    if (params.search) query.append('search', params.search);
    const queryStr = query.toString();
    return http.get(`/admin/promo-codes${queryStr ? '?' + queryStr : ''}`);
  },
  
  // NOTE: Single promo detail - use getAll() and filter client-side instead
  
  create: (data) =>
    http.post('/admin/promo-codes', data),
  
  disable: (codeId) =>
    http.put(`/admin/promo-codes/${codeId}/disable`),
  
  // NOTE: enable() and delete() not available in backend
  
  getRedemptions: (codeId) =>
    http.get(`/admin/promo-codes/${codeId}/redemptions`),
};

// ============================================
// REFERRALS
// ============================================
export const referralsApi = {
  getDashboard: () =>
    http.get('/admin/referrals/dashboard'),
  
  getLedger: (params = {}) => {
    const query = new URLSearchParams();
    if (params.page) query.append('page', params.page);
    if (params.limit) query.append('limit', params.limit);
    const queryStr = query.toString();
    return http.get(`/admin/referrals/ledger${queryStr ? '?' + queryStr : ''}`);
  },
};

// ============================================
// REPORTS
// ============================================
export const reportsApi = {
  // Existing backend endpoints
  getBalanceFlow: (days = 30) =>
    http.get(`/admin/reports/balance-flow?days=${days}`),
  
  getProfitByGame: () =>
    http.get('/admin/reports/profit-by-game'),
  
  getVoids: (days = 30) =>
    http.get(`/admin/reports/voids?days=${days}`),
  
  // These use alternative endpoints that exist
  // Performance → use analytics/platform-trends
  getPerformance: (days = 7) =>
    http.get(`/admin/analytics/platform-trends?days=${days}`),
  
  // Referral stats → use referrals/dashboard
  getReferralStats: () =>
    http.get('/admin/referrals/dashboard'),
  
  // Bonus stats → use analytics/advanced-metrics
  getBonusStats: () =>
    http.get('/admin/analytics/advanced-metrics'),
};

// ============================================
// RULES ENGINE
// ============================================
export const rulesApi = {
  getRules: () =>
    http.get('/admin/rules'),
  
  updateRules: (rules) =>
    http.put('/admin/rules', rules),
};

// ============================================
// API KEYS
// ============================================
export const apiKeysApi = {
  getAll: () =>
    http.get('/admin/system/api-keys'),
  
  create: (data) =>
    http.post('/admin/system/api-keys', data),
  
  revoke: (keyId) =>
    http.delete(`/admin/system/api-keys/${keyId}`),
};

// ============================================
// AUDIT LOGS
// ============================================
export const auditApi = {
  getLogs: async (params = {}) => {
    const query = new URLSearchParams();
    if (params.page) query.append('page', params.page);
    if (params.limit) query.append('limit', params.limit);
    if (params.action) query.append('action', params.action);
    if (params.admin_id) query.append('admin_id', params.admin_id);
    const queryStr = query.toString();
    
    const response = await http.get(`/admin/audit-logs${queryStr ? '?' + queryStr : ''}`);
    
    // Normalize response to handle both array and object responses
    let rawLogs = [];
    if (Array.isArray(response.data)) {
      rawLogs = response.data;
    } else if (response.data?.logs) {
      rawLogs = response.data.logs;
    } else if (response.data?.items) {
      rawLogs = response.data.items;
    }
    
    // Map backend fields to UI expected fields
    const normalizedLogs = rawLogs.map(item => ({
      // Preserve all original fields
      ...item,
      // Normalize to UI expected field names
      log_id: item.log_id || item.id || item._id,
      admin_username: item.admin_username ?? item.username ?? 'System',
      admin_id: item.admin_id ?? item.user_id ?? null,
      action: item.action ?? 'unknown',
      target_type: item.target_type ?? item.resource_type ?? null,
      target_id: item.target_id ?? item.resource_id ?? null,
      timestamp: item.timestamp ?? item.created_at ?? null,
      details: item.details ?? item.metadata ?? null,
    }));
    
    // Return normalized structure
    return {
      ...response,
      data: {
        logs: normalizedLogs,
        total: response.data?.total ?? normalizedLogs.length,
      }
    };
  },
};

// ============================================
// BALANCE CONTROL
// ============================================
export const balanceControlApi = {
  /**
   * Manual load funds to a client's balance
   * Backend: POST /api/v1/admin/balance-control/load
   */
  load: (userId, amount, reason) =>
    http.post('/admin/balance-control/load', { 
      user_id: userId, 
      amount, 
      reason 
    }),
  
  /**
   * Manual withdraw funds from a client's balance
   * Backend: POST /api/v1/admin/balance-control/withdraw
   */
  withdraw: (userId, amount, reason) =>
    http.post('/admin/balance-control/withdraw', { 
      user_id: userId, 
      amount, 
      reason 
    }),
};

// ============================================
// TELEGRAM BOTS
// ============================================
export const telegramApi = {
  getBots: () =>
    http.get('/admin/telegram/bots'),
  
  createBot: (data) =>
    http.post('/admin/telegram/bots', data),
  
  updateBot: (botId, data) =>
    http.put(`/admin/telegram/bots/${botId}`, data),
  
  deleteBot: (botId) =>
    http.delete(`/admin/telegram/bots/${botId}`),
  
  testBot: (botId) =>
    http.post(`/admin/telegram/bots/${botId}/test`),
  
  getEvents: () =>
    http.get('/admin/telegram/events'),
  
  getBotPermissions: (botId) =>
    http.get(`/admin/telegram/bots/${botId}/permissions`),
  
  updateBotPermissions: (botId, permissions) =>
    http.post(`/admin/telegram/bots/${botId}/permissions`, { permissions }),
  
  getLogs: (params = {}) => {
    const query = new URLSearchParams();
    if (params.limit) query.append('limit', params.limit);
    if (params.event_type) query.append('event_type', params.event_type);
    const queryStr = query.toString();
    return http.get(`/admin/telegram/logs${queryStr ? '?' + queryStr : ''}`);
  },
  
  setupWebhook: () =>
    http.post('/admin/telegram/setup-webhook'),
  
  getWebhookInfo: () =>
    http.get('/admin/telegram/webhook-info'),
};

// ============================================
// REWARDS ADMIN
// ============================================
export const rewardsAdminApi = {
  getAll: () =>
    http.get('/admin/rewards'),
  
  getById: (rewardId) =>
    http.get(`/admin/rewards/${rewardId}`),
  
  create: (data) =>
    http.post('/admin/rewards', data),
  
  update: (rewardId, data) =>
    http.put(`/admin/rewards/${rewardId}`, data),
  
  delete: (rewardId) =>
    http.delete(`/admin/rewards/${rewardId}`),
  
  grant: (data) =>
    http.post('/admin/rewards/grant', data),
  
  getGrantHistory: (limit = 100) =>
    http.get(`/admin/rewards/grants/history?limit=${limit}`),
  
  trigger: (triggerType, userId) =>
    http.post(`/admin/rewards/trigger/${triggerType}?user_id=${userId}`),
};

// ============================================
// REFERRAL TIERS
// ============================================
export const referralTiersApi = {
  // Tier management
  getTiers: () =>
    http.get('/admin/referral-tiers/tiers'),
  
  updateTier: (tierId, data) =>
    http.put(`/admin/referral-tiers/tiers/${tierId}`, data),
  
  // Global overrides (campaigns)
  getGlobalOverrides: () =>
    http.get('/admin/referral-tiers/global-overrides'),
  
  createGlobalOverride: (data) =>
    http.post('/admin/referral-tiers/global-overrides', data),
  
  updateGlobalOverride: (overrideId, data) =>
    http.put(`/admin/referral-tiers/global-overrides/${overrideId}`, data),
  
  deleteGlobalOverride: (overrideId) =>
    http.delete(`/admin/referral-tiers/global-overrides/${overrideId}`),
  
  // Client overrides
  getClientOverrides: () =>
    http.get('/admin/referral-tiers/client-overrides'),
  
  createClientOverride: (data) =>
    http.post('/admin/referral-tiers/client-overrides', data),
  
  updateClientOverride: (userId, data) =>
    http.put(`/admin/referral-tiers/client-overrides/${userId}`, data),
  
  deleteClientOverride: (userId) =>
    http.delete(`/admin/referral-tiers/client-overrides/${userId}`),
  
  // Effective bonus calculator
  getEffectiveBonus: (userId) =>
    http.get(`/admin/referral-tiers/effective-bonus/${userId}`),
  
  // User's own tier info
  getMyTier: () =>
    http.get('/admin/referral-tiers/my-tier'),
};

// ============================================
// PROMOTIONS API
// ============================================
export const promotionsApi = {
  // Public endpoints
  getActive: () =>
    http.get('/promotions/active'),
  
  trackView: (promoId) =>
    http.post(`/promotions/track-view/${promoId}`),
  
  trackClick: (promoId) =>
    http.post(`/promotions/track-click/${promoId}`),
  
  // Admin endpoints
  getAll: () =>
    http.get('/promotions/admin/all'),
  
  getStats: () =>
    http.get('/promotions/admin/stats'),
  
  create: (data) =>
    http.post('/promotions/admin', data),
  
  update: (promoId, data) =>
    http.put(`/promotions/admin/${promoId}`, data),
  
  delete: (promoId) =>
    http.delete(`/promotions/admin/${promoId}`),
};

// Default export for convenience
const adminApi = {
  dashboard: dashboardApi,
  users: usersApi,
  analytics: analyticsApi,
  orders: ordersApi,
  approvals: approvalsApi,
  system: systemApi,
  settings: settingsApi,
  games: gamesApi,
  perks: perksApi,
  promoCodes: promoCodesApi,
  referrals: referralsApi,
  referralTiers: referralTiersApi,
  promotions: promotionsApi,
  reports: reportsApi,
  audit: auditApi,
  balanceControl: balanceControlApi,
  telegram: telegramApi,
  rewards: rewardsAdminApi,
  rules: rulesApi,
  apiKeys: apiKeysApi,
};

export default adminApi;

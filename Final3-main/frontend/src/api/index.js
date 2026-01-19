/**
 * API Module - Barrel Export
 * SINGLE SOURCE OF TRUTH for all API utilities
 */

// HTTP Client
export { 
  default as http, 
  safeApiCall, 
  getErrorMessage, 
  isServerUnavailable,
  API_URL, 
  API_V1 
} from './http';

// Client API Endpoints
export {
  authApi,
  walletApi,
  transactionsApi,
  gamesApi,
  referralsApi,
  rewardsApi,
  portalApi,
} from './endpoints';

// Admin API Endpoints
export {
  default as adminApi,
  dashboardApi,
  usersApi,
  ordersApi,
  approvalsApi,
  systemApi,
  settingsApi,
  gamesApi as adminGamesApi,
  perksApi,
  promoCodesApi,
  reportsApi,
  auditApi,
  balanceControlApi,
} from './admin';

// Safe fetch helpers
export {
  fetchWalletBalance,
  fetchRecentTransactions,
  fetchPublicGames,
  fetchReferralDetails,
} from './endpoints';

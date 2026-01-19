/**
 * Route Constants
 * Single source of truth for all application routes
 */

export const ROUTES = {
  // Public Routes
  PUBLIC: {
    HOME: '/',
    GAMES: '/games',
    LOGIN: '/login',
    REGISTER: '/register',
    ADMIN_LOGIN: '/admin/login',
  },

  // Client Routes (Protected)
  CLIENT: {
    HOME: '/client/home',
    WALLET: '/client/wallet',
    WALLET_ADD: '/client/wallet/add',
    WALLET_WITHDRAW: '/client/wallet/withdraw',
    WALLET_TRANSACTION: '/client/wallet/transaction/:orderId',
    GAMES: '/client/games',
    REFERRALS: '/client/referrals',
    PROFILE: '/client/profile',
  },

  // Portal Routes (Legacy - redirects to client)
  PORTAL: {
    ROOT: '/portal',
    DASHBOARD: '/portal/dashboard',
    WALLET: '/portal/wallet',
    WALLETS: '/portal/wallets',
    TRANSACTIONS: '/portal/transactions',
    REFERRALS: '/portal/referrals',
    REWARDS: '/portal/rewards',
    CREDENTIALS: '/portal/credentials',
    WITHDRAWALS: '/portal/withdrawals',
    SECURITY: '/portal/security',
    GAMES: '/portal/load-game',
    BONUS_TASKS: '/portal/bonus-tasks',
  },

  // Admin Routes (Protected - Admin Only)
  ADMIN: {
    ROOT: '/admin',
    DASHBOARD: '/admin',
    APPROVALS: '/admin/approvals',
    ORDERS: '/admin/orders',
    CLIENTS: '/admin/clients',
    CLIENT_NEW: '/admin/clients/new',
    CLIENT_DETAIL: '/admin/clients/:clientId',
    GAMES: '/admin/games',
    RULES: '/admin/rules',
    REFERRALS: '/admin/referrals',
    PROMO_CODES: '/admin/promo-codes',
    BALANCE_CONTROL: '/admin/balance-control',
    REPORTS: '/admin/reports',
    SYSTEM: '/admin/system',
    AUDIT_LOGS: '/admin/audit-logs',
    // System Subsections
    SYSTEM_WEBHOOKS: '/admin/system/webhooks',
    SYSTEM_API_ACCESS: '/admin/system/api-access',
    SYSTEM_DOCUMENTATION: '/admin/system/documentation',
    SYSTEM_REWARDS: '/admin/system/rewards',
    SYSTEM_AUTOMATIONS: '/admin/system/automations',
    SYSTEM_PAYMENT_METHODS: '/admin/system/payment-methods',
    SYSTEM_TELEGRAM: '/admin/system/telegram-bots',
    SYSTEM_PAYMENT_QR: '/admin/system/payment-qr',
    SYSTEM_WALLET_LOADS: '/admin/system/wallet-loads',
  },

  // Magic Links
  MAGIC: {
    PORTAL_LANDING: '/p/:token',
  },
};

/**
 * Helper to generate dynamic routes
 */
export const generateRoute = {
  clientTransaction: (orderId) => `/client/wallet/transaction/${orderId}`,
  adminClientDetail: (clientId) => `/admin/clients/${clientId}`,
  portalLanding: (token) => `/p/${token}`,
};

export default ROUTES;

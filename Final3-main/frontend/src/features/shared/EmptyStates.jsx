/**
 * Empty States Components
 * Reusable empty state displays for better UX
 */

import React from 'react';
import { 
  Inbox, 
  Search, 
  FileX, 
  Users, 
  Wallet, 
  Gamepad2,
  Clock,
  AlertCircle 
} from 'lucide-react';

const iconMap = {
  inbox: Inbox,
  search: Search,
  file: FileX,
  users: Users,
  wallet: Wallet,
  games: Gamepad2,
  clock: Clock,
  error: AlertCircle,
};

/**
 * Generic empty state component
 */
export const EmptyState = ({ 
  icon = 'inbox',
  title = 'No data found',
  description,
  action,
  actionLabel,
  className = '',
}) => {
  const Icon = typeof icon === 'string' ? iconMap[icon] : icon;
  
  return (
    <div className={`flex flex-col items-center justify-center py-12 px-4 text-center ${className}`}>
      <div className="w-16 h-16 bg-white/[0.02] border border-white/5 rounded-2xl flex items-center justify-center mb-4">
        <Icon className="w-8 h-8 text-gray-600" />
      </div>
      <h3 className="text-lg font-medium text-white mb-2">{title}</h3>
      {description && (
        <p className="text-sm text-gray-500 max-w-xs mb-4">{description}</p>
      )}
      {action && actionLabel && (
        <button
          onClick={action}
          className="px-4 py-2 bg-violet-600 hover:bg-violet-500 text-white text-sm font-medium rounded-lg transition-colors"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
};

/**
 * No transactions state
 */
export const NoTransactions = ({ onAddFunds }) => (
  <EmptyState
    icon="clock"
    title="No transactions yet"
    description="Your transaction history will appear here once you start using your wallet."
    action={onAddFunds}
    actionLabel="Add Funds"
  />
);

/**
 * No games state
 */
export const NoGames = () => (
  <EmptyState
    icon="games"
    title="No games available"
    description="Games will be available here once configured by the administrator."
  />
);

/**
 * No referrals state
 */
export const NoReferrals = ({ onCopyLink }) => (
  <EmptyState
    icon="users"
    title="No referrals yet"
    description="Share your referral link to start earning rewards when your friends join."
    action={onCopyLink}
    actionLabel="Copy Referral Link"
  />
);

/**
 * Search no results state
 */
export const NoSearchResults = ({ query, onClear }) => (
  <EmptyState
    icon="search"
    title="No results found"
    description={`We couldn't find anything matching "${query}". Try a different search term.`}
    action={onClear}
    actionLabel="Clear Search"
  />
);

/**
 * Error state
 */
export const ErrorState = ({ 
  title = 'Something went wrong',
  description = 'An error occurred while loading the data.',
  onRetry,
}) => (
  <EmptyState
    icon="error"
    title={title}
    description={description}
    action={onRetry}
    actionLabel="Try Again"
    className="text-red-400"
  />
);

export default EmptyState;

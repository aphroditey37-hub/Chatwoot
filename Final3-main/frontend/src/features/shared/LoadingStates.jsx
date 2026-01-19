/**
 * Loading States Components
 * Reusable loading indicators for consistent UX
 */

import React from 'react';
import { RefreshCw, Loader2 } from 'lucide-react';

/**
 * Full page loading spinner
 */
export const PageLoader = ({ message = 'Loading...' }) => (
  <div className="min-h-screen bg-[#0a0a0f] flex flex-col items-center justify-center gap-4">
    <RefreshCw className="w-8 h-8 text-violet-500 animate-spin" />
    {message && <p className="text-gray-400 text-sm">{message}</p>}
  </div>
);

/**
 * Inline loading spinner
 */
export const InlineLoader = ({ size = 'md', className = '' }) => {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8',
  };
  
  return (
    <Loader2 className={`animate-spin text-violet-500 ${sizeClasses[size]} ${className}`} />
  );
};

/**
 * Button loading state
 */
export const ButtonLoader = ({ children, loading, className = '' }) => (
  <span className={`flex items-center justify-center gap-2 ${className}`}>
    {loading && <Loader2 className="w-4 h-4 animate-spin" />}
    {children}
  </span>
);

/**
 * Skeleton loader for cards
 */
export const CardSkeleton = ({ lines = 3, className = '' }) => (
  <div className={`animate-pulse ${className}`}>
    <div className="h-4 bg-white/5 rounded w-3/4 mb-4"></div>
    {Array.from({ length: lines }).map((_, i) => (
      <div 
        key={i} 
        className="h-3 bg-white/5 rounded mb-2" 
        style={{ width: `${100 - (i * 15)}%` }}
      ></div>
    ))}
  </div>
);

/**
 * List skeleton loader
 */
export const ListSkeleton = ({ items = 5, className = '' }) => (
  <div className={`space-y-3 ${className}`}>
    {Array.from({ length: items }).map((_, i) => (
      <div key={i} className="flex items-center gap-3 p-4 bg-white/[0.02] rounded-xl animate-pulse">
        <div className="w-10 h-10 bg-white/5 rounded-xl"></div>
        <div className="flex-1">
          <div className="h-4 bg-white/5 rounded w-1/2 mb-2"></div>
          <div className="h-3 bg-white/5 rounded w-1/3"></div>
        </div>
        <div className="h-4 bg-white/5 rounded w-16"></div>
      </div>
    ))}
  </div>
);

export default PageLoader;

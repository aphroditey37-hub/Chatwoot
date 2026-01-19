/**
 * Loader - Loading States
 */

import React from 'react';
import { Loader2 } from 'lucide-react';

// Spinner Loader
export const Spinner = ({ size = 'md', className = '' }) => {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8',
    xl: 'w-12 h-12',
  };

  return (
    <Loader2 
      className={[
        'animate-spin text-violet-500',
        sizeClasses[size] || sizeClasses.md,
        className
      ].join(' ')} 
    />
  );
};

// Skeleton Loader
export const Skeleton = ({ className = '', variant = 'text' }) => {
  const variantClasses = {
    text: 'h-4 rounded',
    title: 'h-6 rounded',
    avatar: 'w-10 h-10 rounded-full',
    card: 'h-32 rounded-2xl',
    button: 'h-10 w-24 rounded-xl',
  };

  return (
    <div 
      className={[
        'bg-white/5 animate-pulse',
        variantClasses[variant] || variantClasses.text,
        className
      ].join(' ')} 
    />
  );
};

// Page Loader
const Loader = ({ message = 'Loading...' }) => (
  <div className="min-h-screen bg-[#0a0a0f] flex flex-col items-center justify-center">
    <Spinner size="xl" />
    <p className="mt-4 text-gray-400 text-sm">{message}</p>
  </div>
);

export default Loader;

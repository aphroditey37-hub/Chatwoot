/**
 * Card - Unified Card Component
 * Consistent styling across all pages
 */

import React from 'react';

const Card = ({
  children,
  className = '',
  hover = false,
  gradient = false,
  padding = 'md',
  ...props
}) => {
  const paddingClasses = {
    none: '',
    sm: 'p-3',
    md: 'p-4',
    lg: 'p-6',
  };

  const baseClasses = [
    'bg-white/[0.02] border border-white/5 rounded-2xl',
    hover ? 'hover:bg-white/[0.04] hover:border-white/10 transition-all cursor-pointer' : '',
    gradient ? 'bg-gradient-to-br from-violet-900/40 via-fuchsia-900/30 to-violet-900/40 border-violet-500/20' : '',
    paddingClasses[padding] || paddingClasses.md,
    className
  ].filter(Boolean).join(' ');

  return (
    <div className={baseClasses} {...props}>
      {children}
    </div>
  );
};

const CardHeader = ({ children, className = '' }) => (
  <div className={`flex items-center justify-between mb-4 ${className}`}>
    {children}
  </div>
);

const CardTitle = ({ children, className = '' }) => (
  <h3 className={`text-sm font-semibold text-white ${className}`}>
    {children}
  </h3>
);

const CardContent = ({ children, className = '' }) => (
  <div className={className}>
    {children}
  </div>
);

Card.Header = CardHeader;
Card.Title = CardTitle;
Card.Content = CardContent;

export default Card;

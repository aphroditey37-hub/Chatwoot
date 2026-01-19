/**
 * Badge - Status Badge Component
 * For transaction status, user status, etc.
 */

import React from 'react';

const Badge = ({ children, variant = 'default', size = 'sm', className = '' }) => {
  const variantClasses = {
    default: 'bg-gray-500/10 text-gray-400',
    success: 'bg-emerald-500/10 text-emerald-400',
    warning: 'bg-amber-500/10 text-amber-400',
    error: 'bg-red-500/10 text-red-400',
    info: 'bg-blue-500/10 text-blue-400',
    primary: 'bg-violet-500/10 text-violet-400',
    // Status-specific
    approved: 'bg-emerald-500/10 text-emerald-400',
    completed: 'bg-emerald-500/10 text-emerald-400',
    pending: 'bg-amber-500/10 text-amber-400',
    pending_approval: 'bg-amber-500/10 text-amber-400',
    rejected: 'bg-red-500/10 text-red-400',
    cancelled: 'bg-red-500/10 text-red-400',
    active: 'bg-blue-500/10 text-blue-400',
    inactive: 'bg-gray-500/10 text-gray-400',
    credited: 'bg-emerald-500/10 text-emerald-400',
  };

  const sizeClasses = {
    xs: 'px-1.5 py-0.5 text-[10px]',
    sm: 'px-2 py-1 text-xs',
    md: 'px-2.5 py-1.5 text-sm',
  };

  const classes = [
    'inline-flex items-center font-medium rounded-lg',
    variantClasses[variant] || variantClasses.default,
    sizeClasses[size] || sizeClasses.sm,
    className
  ].join(' ');

  return <span className={classes}>{children}</span>;
};

// Helper to get badge from status string
Badge.fromStatus = (status) => {
  const statusMap = {
    approved: { variant: 'approved', label: 'Approved' },
    completed: { variant: 'completed', label: 'Completed' },
    pending: { variant: 'pending', label: 'Pending' },
    pending_approval: { variant: 'pending_approval', label: 'Pending' },
    rejected: { variant: 'rejected', label: 'Rejected' },
    cancelled: { variant: 'cancelled', label: 'Cancelled' },
    active: { variant: 'active', label: 'Active' },
    inactive: { variant: 'inactive', label: 'Inactive' },
    credited: { variant: 'credited', label: 'Credited' },
  };

  const config = statusMap[status?.toLowerCase()] || { variant: 'default', label: status || 'Unknown' };
  return <Badge variant={config.variant}>{config.label}</Badge>;
};

export default Badge;

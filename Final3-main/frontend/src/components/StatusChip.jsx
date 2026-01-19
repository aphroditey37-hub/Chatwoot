import React from 'react';
import { cn } from '../lib/utils';
import { Clock, CheckCircle, XCircle, AlertCircle } from 'lucide-react';

export const StatusChip = ({ status, className, ...props }) => {
  const normalizedStatus = status?.toLowerCase().replace(/_/g, ' ') || 'unknown';
  
  const statusConfig = {
    // Pending states
    'pending': {
      label: 'Pending',
      icon: Clock,
      className: 'bg-[hsl(var(--warning-bg))] text-[hsl(var(--warning))] border-[hsl(var(--warning)_/_0.3)]',
    },
    'pending review': {
      label: 'Pending Review',
      icon: Clock,
      className: 'bg-[hsl(var(--warning-bg))] text-[hsl(var(--warning))] border-[hsl(var(--warning)_/_0.3)]',
    },
    'initiated': {
      label: 'Initiated',
      icon: Clock,
      className: 'bg-[hsl(var(--info-bg))] text-[hsl(var(--info))] border-[hsl(var(--info)_/_0.3)]',
    },
    'awaiting payment proof': {
      label: 'Awaiting Proof',
      icon: Clock,
      className: 'bg-[hsl(var(--warning-bg))] text-[hsl(var(--warning))] border-[hsl(var(--warning)_/_0.3)]',
    },
    
    // Approved states
    'approved': {
      label: 'Approved',
      icon: CheckCircle,
      className: 'bg-[hsl(var(--success-bg))] text-[hsl(var(--success))] border-[hsl(var(--success)_/_0.3)]',
    },
    'approved executed': {
      label: 'Approved',
      icon: CheckCircle,
      className: 'bg-[hsl(var(--success-bg))] text-[hsl(var(--success))] border-[hsl(var(--success)_/_0.3)]',
    },
    'approved failed': {
      label: 'Failed',
      icon: AlertCircle,
      className: 'bg-[hsl(var(--error-bg))] text-[hsl(var(--error))] border-[hsl(var(--error)_/_0.3)]',
    },
    
    // Rejected state
    'rejected': {
      label: 'Rejected',
      icon: XCircle,
      className: 'bg-[hsl(var(--error-bg))] text-[hsl(var(--error))] border-[hsl(var(--error)_/_0.3)]',
    },
    
    // Completed
    'completed': {
      label: 'Completed',
      icon: CheckCircle,
      className: 'bg-[hsl(var(--success-bg))] text-[hsl(var(--success))] border-[hsl(var(--success)_/_0.3)]',
    },
    
    // Failed
    'failed': {
      label: 'Failed',
      icon: XCircle,
      className: 'bg-[hsl(var(--error-bg))] text-[hsl(var(--error))] border-[hsl(var(--error)_/_0.3)]',
    },
  };
  
  const config = statusConfig[normalizedStatus] || {
    label: status || 'Unknown',
    icon: AlertCircle,
    className: 'bg-[hsl(var(--muted))] text-[hsl(var(--text-muted))] border-[hsl(var(--border))]',
  };
  
  const Icon = config.icon;
  
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border",
        "whitespace-nowrap",
        config.className,
        className
      )}
      {...props}
    >
      <Icon className="w-3 h-3" />
      {config.label}
    </span>
  );
};

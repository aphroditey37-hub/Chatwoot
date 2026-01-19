import React from 'react';
import { cn } from '../lib/utils';

export const SoftInput = ({ 
  className, 
  type = 'text',
  label,
  error,
  icon: Icon,
  ...props 
}) => {
  return (
    <div className="w-full">
      {label && (
        <label className="block text-sm font-medium text-[hsl(var(--text-secondary))] mb-2">
          {label}
        </label>
      )}
      <div className="relative">
        {Icon && (
          <div className="absolute left-4 top-1/2 -translate-y-1/2 text-[hsl(var(--text-muted))]">
            <Icon className="w-5 h-5" />
          </div>
        )}
        <input
          type={type}
          className={cn(
            "w-full rounded-[14px] border border-[hsl(var(--border))] bg-[hsl(var(--surface-elevated))]",
            "px-4 py-3 min-h-[52px]",
            "text-base text-[hsl(var(--foreground))] placeholder:text-[hsl(var(--text-dim))]",
            "transition-all duration-200",
            "focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))] focus:ring-opacity-30 focus:border-[hsl(var(--primary))]",
            "focus:shadow-[0_0_20px_hsl(var(--primary)_/_0.2)]",
            Icon && "pl-12",
            error && "border-[hsl(var(--error))] focus:ring-[hsl(var(--error))]",
            className
          )}
          {...props}
        />
      </div>
      {error && (
        <p className="mt-1.5 text-sm text-[hsl(var(--error))]">{error}</p>
      )}
    </div>
  );
};

export const SoftTextarea = ({ 
  className, 
  label,
  error,
  rows = 4,
  ...props 
}) => {
  return (
    <div className="w-full">
      {label && (
        <label className="block text-sm font-medium text-[hsl(var(--text-secondary))] mb-2">
          {label}
        </label>
      )}
      <textarea
        rows={rows}
        className={cn(
          "w-full rounded-[14px] border border-[hsl(var(--border))] bg-[hsl(var(--surface-elevated))]",
          "px-4 py-3",
          "text-base text-[hsl(var(--foreground))] placeholder:text-[hsl(var(--text-dim))]",
          "transition-all duration-200",
          "focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))] focus:ring-opacity-30 focus:border-[hsl(var(--primary))]",
          "focus:shadow-[0_0_20px_hsl(var(--primary)_/_0.2)]",
          "resize-none",
          error && "border-[hsl(var(--error))] focus:ring-[hsl(var(--error))]",
          className
        )}
        {...props}
      />
      {error && (
        <p className="mt-1.5 text-sm text-[hsl(var(--error))]">{error}</p>
      )}
    </div>
  );
};

export const SoftSelect = ({ 
  className, 
  label,
  error,
  children,
  ...props 
}) => {
  return (
    <div className="w-full">
      {label && (
        <label className="block text-sm font-medium text-[hsl(var(--text-secondary))] mb-2">
          {label}
        </label>
      )}
      <select
        className={cn(
          "w-full rounded-[14px] border border-[hsl(var(--border))] bg-[hsl(var(--surface-elevated))]",
          "px-4 py-3 min-h-[52px]",
          "text-base text-[hsl(var(--foreground))]",
          "transition-all duration-200",
          "focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))] focus:ring-opacity-30 focus:border-[hsl(var(--primary))]",
          "focus:shadow-[0_0_20px_hsl(var(--primary)_/_0.2)]",
          "cursor-pointer",
          error && "border-[hsl(var(--error))] focus:ring-[hsl(var(--error))]",
          className
        )}
        {...props}
      >
        {children}
      </select>
      {error && (
        <p className="mt-1.5 text-sm text-[hsl(var(--error))]">{error}</p>
      )}
    </div>
  );
};

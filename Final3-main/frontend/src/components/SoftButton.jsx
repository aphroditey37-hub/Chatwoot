import React from 'react';
import { cn } from '../lib/utils';

export const SoftButton = ({ 
  children, 
  className, 
  variant = 'primary',
  size = 'default',
  fullWidth = false,
  icon: Icon,
  disabled = false,
  ...props 
}) => {
  const baseStyles = "inline-flex items-center justify-center gap-2 font-semibold rounded-[14px] transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed";
  
  const sizeStyles = {
    sm: "px-4 py-2 text-sm min-h-[40px]",
    default: "px-6 py-3 text-sm min-h-[48px]",
    lg: "px-8 py-4 text-base min-h-[56px]",
  };
  
  const variantStyles = {
    primary: "bg-[hsl(var(--primary))] text-white shadow-[0_4px_16px_hsl(var(--primary)_/_0.3)] hover:bg-[hsl(var(--primary-hover))] hover:shadow-[0_6px_20px_hsl(var(--primary)_/_0.4)] hover:-translate-y-0.5 active:translate-y-0",
    secondary: "bg-[hsl(var(--surface-elevated))] text-[hsl(var(--foreground))] border border-[hsl(var(--border))] hover:bg-[hsl(var(--surface-secondary))] hover:border-[hsl(var(--border-soft))]",
    ghost: "bg-transparent text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-elevated))] hover:text-[hsl(var(--foreground))]",
    danger: "bg-[hsl(var(--error))] text-white shadow-[0_4px_16px_hsl(var(--error)_/_0.3)] hover:opacity-90",
  };
  
  return (
    <button
      className={cn(
        baseStyles,
        sizeStyles[size],
        variantStyles[variant],
        fullWidth && "w-full",
        className
      )}
      disabled={disabled}
      {...props}
    >
      {Icon && <Icon className="w-[18px] h-[18px]" />}
      {children}
    </button>
  );
};

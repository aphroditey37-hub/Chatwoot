import React from 'react';
import { cn } from '../lib/utils';

export const SoftCard = ({ 
  children, 
  className, 
  hover = false, 
  interactive = false,
  glow = false,
  ...props 
}) => {
  return (
    <div
      className={cn(
        "rounded-[16px] border border-[hsl(var(--border))] bg-[hsl(var(--surface-primary))] p-5",
        "shadow-[0_8px_24px_hsl(220_20%_5%_/_0.4),_0_2px_8px_hsl(220_20%_5%_/_0.2)]",
        hover && "transition-all duration-300 hover:border-[hsl(var(--border-soft))] hover:shadow-[0_12px_32px_hsl(220_20%_5%_/_0.5)]",
        interactive && "cursor-pointer transition-all duration-300 hover:border-[hsl(var(--primary-border))] hover:bg-[hsl(var(--surface-elevated))]",
        glow && "border-[hsl(var(--primary-border))] shadow-[0_8px_24px_hsl(220_20%_5%_/_0.4),_0_0_20px_hsl(var(--primary)_/_0.2)]",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
};

export const SoftCardHeader = ({ children, className, ...props }) => {
  return (
    <div
      className={cn(
        "flex items-center justify-between mb-4",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
};

export const SoftCardTitle = ({ children, className, icon: Icon, ...props }) => {
  return (
    <h3
      className={cn(
        "text-base font-semibold text-[hsl(var(--foreground))] flex items-center gap-2",
        className
      )}
      {...props}
    >
      {Icon && <Icon className="w-5 h-5 text-[hsl(var(--primary))]" />}
      {children}
    </h3>
  );
};

export const SoftCardContent = ({ children, className, ...props }) => {
  return (
    <div
      className={cn("space-y-4", className)}
      {...props}
    >
      {children}
    </div>
  );
};

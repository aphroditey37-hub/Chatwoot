import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { cn } from '../lib/utils';
import { Home, Wallet, Receipt, Users, Gift } from 'lucide-react';

export const FloatingBottomNav = () => {
  const navigate = useNavigate();
  const location = useLocation();
  
  const navItems = [
    { id: 'home', label: 'Home', icon: Home, path: '/portal' },
    { id: 'wallet', label: 'Wallet', icon: Wallet, path: '/portal/wallet' },
    { id: 'history', label: 'History', icon: Receipt, path: '/portal/transactions' },
    { id: 'referrals', label: 'Referrals', icon: Users, path: '/portal/referrals' },
    { id: 'rewards', label: 'Rewards', icon: Gift, path: '/portal/rewards' },
  ];
  
  const isActive = (path) => {
    if (path === '/portal') return location.pathname === '/portal';
    return location.pathname.startsWith(path);
  };
  
  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-50 lg:hidden"
      style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}
    >
      <div className="mx-4 mb-4">
        <div className="bg-[hsl(var(--surface-primary))] border border-[hsl(var(--border))] rounded-[22px] shadow-[0_8px_24px_hsl(220_20%_5%_/_0.4),_0_4px_12px_hsl(220_20%_5%_/_0.3)] backdrop-blur-xl">
          <div className="flex items-center justify-around px-2 py-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = isActive(item.path);
              
              return (
                <button
                  key={item.id}
                  onClick={() => navigate(item.path)}
                  className={cn(
                    "flex flex-col items-center justify-center gap-1 px-3 py-2.5 rounded-[16px] transition-all duration-200 min-w-[60px]",
                    active 
                      ? "bg-[hsl(var(--primary))] text-white shadow-[0_4px_12px_hsl(var(--primary)_/_0.4)]" 
                      : "text-[hsl(var(--text-muted))] hover:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-elevated))]"
                  )}
                  data-testid={`bottom-nav-${item.id}`}
                >
                  <Icon className={cn("w-5 h-5", active ? "stroke-[2.5]" : "stroke-[2]")} />
                  <span className={cn(
                    "text-[10px] font-semibold leading-none",
                    active ? "font-bold" : "font-medium"
                  )}>
                    {item.label}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </nav>
  );
};

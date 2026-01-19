/**
 * ClientBottomNav - Mobile Bottom Navigation for Client Area
 * Shared component - REFERRALS IS PRIORITY (next to Home)
 * 
 * Order: Home | Referrals | Wallet | Games | Profile
 */

import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Home, Users, Wallet, Gamepad2, User } from 'lucide-react';

// Navigation items with Referrals prioritized
const navItems = [
  { id: 'home', icon: Home, label: 'Home', path: '/client/home' },
  { id: 'referrals', icon: Users, label: 'Referrals', path: '/client/referrals' },
  { id: 'wallet', icon: Wallet, label: 'Wallet', path: '/client/wallet' },
  { id: 'games', icon: Gamepad2, label: 'Games', path: '/client/games' },
  { id: 'profile', icon: User, label: 'Profile', path: '/client/profile' },
];

export const ClientBottomNav = ({ active }) => {
  const navigate = useNavigate();
  const location = useLocation();
  
  // Auto-detect active tab from URL if not provided
  const getActiveTab = () => {
    if (active) return active;
    
    const path = location.pathname;
    if (path.includes('/referrals')) return 'referrals';
    if (path.includes('/wallet')) return 'wallet';
    if (path.includes('/games')) return 'games';
    if (path.includes('/profile')) return 'profile';
    return 'home';
  };
  
  const activeTab = getActiveTab();

  return (
    <nav 
      className="fixed bottom-0 left-0 right-0 z-50 bg-[#0d0d12]/95 backdrop-blur-xl border-t border-white/5"
      style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
      data-testid="client-bottom-nav"
    >
      <div className="flex items-center justify-around h-16 max-w-lg mx-auto">
        {navItems.map(item => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          
          return (
            <button
              key={item.id}
              onClick={() => navigate(item.path)}
              className={`relative flex flex-col items-center justify-center gap-1 w-16 h-full transition-all ${
                isActive ? 'text-violet-400' : 'text-gray-500 hover:text-gray-300'
              }`}
              data-testid={`nav-${item.id}`}
            >
              <Icon className={`w-5 h-5 ${isActive ? 'scale-110' : ''} transition-transform`} />
              <span className="text-[10px] font-medium">{item.label}</span>
              {isActive && (
                <div className="absolute top-0 w-8 h-0.5 bg-violet-500 rounded-full" />
              )}
            </button>
          );
        })}
      </div>
    </nav>
  );
};

export default ClientBottomNav;

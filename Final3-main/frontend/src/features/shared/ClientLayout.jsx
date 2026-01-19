/**
 * ClientLayout - Wrapper Layout for Client Pages
 * Provides consistent structure with bottom navigation
 */

import React from 'react';
import { ClientBottomNav } from './ClientBottomNav';

export const ClientLayout = ({ 
  children, 
  activeNav,
  title,
  showHeader = true,
  headerRight,
  className = '',
}) => {
  return (
    <div className={`min-h-screen bg-[#0a0a0f] pb-20 ${className}`}>
      {/* Header */}
      {showHeader && title && (
        <header className="sticky top-0 z-40 bg-[#0a0a0f]/90 backdrop-blur-xl border-b border-white/5">
          <div className="px-4 py-4 flex items-center justify-between">
            <h1 className="text-xl font-bold text-white">{title}</h1>
            {headerRight}
          </div>
        </header>
      )}

      {/* Main Content */}
      <main className="px-4 py-6">
        {children}
      </main>

      {/* Bottom Navigation */}
      <ClientBottomNav active={activeNav} />
    </div>
  );
};

export default ClientLayout;

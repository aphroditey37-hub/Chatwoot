/**
 * ReferralBanner - Prominent Referral CTA Banner for Home Page
 * HIGH PRIORITY: Shows immediately below wallet card
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Users, ChevronRight, Sparkles } from 'lucide-react';

export const ReferralBanner = ({ className = '' }) => {
  const navigate = useNavigate();

  return (
    <button
      onClick={() => navigate('/client/referrals')}
      className={[
        'w-full relative overflow-hidden rounded-2xl p-4',
        'bg-gradient-to-r from-violet-600 via-fuchsia-600 to-emerald-500',
        'hover:shadow-lg hover:shadow-violet-500/20 transition-all',
        'group',
        className
      ].join(' ')}
      data-testid="referral-banner-cta"
    >
      {/* Animated background particles */}
      <div className="absolute inset-0 opacity-20">
        <div className="absolute top-2 right-8 w-20 h-20 bg-white rounded-full blur-2xl animate-pulse" />
        <div className="absolute bottom-2 left-8 w-16 h-16 bg-white rounded-full blur-2xl animate-pulse delay-300" />
      </div>

      <div className="relative flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 bg-white/20 backdrop-blur rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform">
            <Users className="w-6 h-6 text-white" />
          </div>
          <div className="text-left">
            <div className="flex items-center gap-1.5">
              <Sparkles className="w-4 h-4 text-amber-300" />
              <span className="text-xs font-medium text-amber-200">Turn Your Network Into Rewards</span>
            </div>
            <h3 className="text-base font-bold text-white">Invite Friends & Earn</h3>
            <p className="text-xs text-white/70">Earn bonuses every time your friends deposit and play</p>
          </div>
        </div>
        <div className="flex items-center gap-1 text-white/90 group-hover:translate-x-1 transition-transform">
          <span className="text-sm font-medium hidden sm:block">Invite Now</span>
          <ChevronRight className="w-5 h-5" />
        </div>
      </div>
    </button>
  );
};

export default ReferralBanner;

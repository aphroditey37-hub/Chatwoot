/**
 * Admin Perks Page
 * DEPRECATED: Perks functionality not available in backend v2
 * Redirects users to the Rewards system or Referral Tiers instead
 */
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Gift, AlertTriangle, ArrowRight, Settings, Users } from 'lucide-react';

export default function AdminPerksPage() {
  const navigate = useNavigate();

  return (
    <div className="space-y-6" data-testid="admin-perks-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <Gift className="w-7 h-7 text-purple-400" />
            Perks & Bonuses
          </h1>
          <p className="text-gray-400">Legacy perks management</p>
        </div>
      </div>

      {/* Deprecation Notice */}
      <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-6">
        <div className="flex items-start gap-4">
          <AlertTriangle className="w-8 h-8 text-amber-400 flex-shrink-0" />
          <div>
            <h3 className="text-amber-400 font-bold text-lg mb-2">Feature Migrated</h3>
            <p className="text-amber-300/80 mb-4">
              The Perks functionality has been migrated to the new <strong>Referral Tiers</strong> and <strong>Rewards</strong> systems. 
              These provide more powerful features including:
            </p>
            <ul className="text-amber-300/80 mb-6 space-y-1">
              <li>• Tiered referral bonuses (Starter → Ruby)</li>
              <li>• Global and individual overrides</li>
              <li>• Time-based promotional campaigns</li>
              <li>• Flexible reward triggers</li>
            </ul>
            
            <div className="flex flex-wrap gap-3">
              <button
                onClick={() => navigate('/admin/referrals')}
                className="flex items-center gap-2 px-4 py-2 bg-purple-500 hover:bg-purple-600 text-white rounded-lg transition"
                data-testid="go-to-referrals-btn"
              >
                <Users className="w-4 h-4" />
                Referral Tiers & Overrides
                <ArrowRight className="w-4 h-4" />
              </button>
              
              <button
                onClick={() => navigate('/admin/system/rewards')}
                className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition"
                data-testid="go-to-rewards-btn"
              >
                <Gift className="w-4 h-4" />
                Rewards Management
                <ArrowRight className="w-4 h-4" />
              </button>
              
              <button
                onClick={() => navigate('/admin/rules')}
                className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition"
                data-testid="go-to-rules-btn"
              >
                <Settings className="w-4 h-4" />
                Rules Engine
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Feature Comparison */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <h3 className="text-white font-bold mb-4">What's New</h3>
        <div className="grid md:grid-cols-2 gap-6">
          <div className="bg-gray-800/50 rounded-lg p-4">
            <h4 className="text-purple-400 font-semibold mb-2">Referral Tier System</h4>
            <p className="text-gray-400 text-sm">
              5-tier progression system (Starter → Ruby) with escalating bonus percentages. 
              Supports global campaign overrides and individual client customization.
            </p>
          </div>
          <div className="bg-gray-800/50 rounded-lg p-4">
            <h4 className="text-emerald-400 font-semibold mb-2">Rewards System</h4>
            <p className="text-gray-400 text-sm">
              Trigger-based rewards for signup, deposits, referrals, and custom events. 
              Supports one-time and recurring rewards with full audit logging.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

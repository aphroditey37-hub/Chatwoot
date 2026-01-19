/**
 * ClientRewards - Rewards Hub Page
 * Route: /client/rewards
 * 
 * Features:
 * - Welcome bonus claim
 * - Promo code redemption
 * - Promo history
 * - Referral rewards summary
 * - Rewards list
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { 
  Gift, Sparkles, Users, ChevronRight, ArrowLeft,
  Ticket, CheckCircle, Clock, AlertCircle, Loader2,
  Copy, Check, History
} from 'lucide-react';

// API
import { rewardsApi, referralsApi, getErrorMessage } from '../../api';
import { ClientBottomNav } from '../../features/shared/ClientBottomNav';

// Loading skeleton component
const Skeleton = ({ className = '' }) => (
  <div className={`bg-white/5 animate-pulse rounded ${className}`} />
);

const ClientRewards = () => {
  const navigate = useNavigate();
  
  // Welcome Credit State
  const [welcomeCredit, setWelcomeCredit] = useState(null);
  const [welcomeLoading, setWelcomeLoading] = useState(true);
  const [claimingWelcome, setClaimingWelcome] = useState(false);
  
  // Promo Code State
  const [promoCode, setPromoCode] = useState('');
  const [promoSubmitting, setPromoSubmitting] = useState(false);
  const [promoHistory, setPromoHistory] = useState([]);
  const [showPromoHistory, setShowPromoHistory] = useState(false);
  const [promoHistoryLoading, setPromoHistoryLoading] = useState(false);
  const [redeemResult, setRedeemResult] = useState(null); // { status: "success" | "error", message: string }
  
  // Referral State
  const [referralStats, setReferralStats] = useState(null);
  const [referralLoading, setReferralLoading] = useState(true);
  
  // Rewards State
  const [rewards, setRewards] = useState([]);
  const [rewardsLoading, setRewardsLoading] = useState(true);
  
  // Error State
  const [error, setError] = useState(null);

  // Fetch Welcome Credit
  const fetchWelcomeCredit = useCallback(async () => {
    setWelcomeLoading(true);
    try {
      const res = await rewardsApi.getWelcomeCredit();
      setWelcomeCredit(res.data);
    } catch (err) {
      console.error('Welcome credit error:', err);
      setWelcomeCredit({ has_credit: false });
    } finally {
      setWelcomeLoading(false);
    }
  }, []);

  // Claim Welcome Credit
  const handleClaimWelcome = async () => {
    setClaimingWelcome(true);
    try {
      const res = await rewardsApi.claimWelcomeCredit();
      toast.success(res.data.message || 'Welcome bonus claimed!');
      setWelcomeCredit({ ...welcomeCredit, has_credit: false, claimed: true });
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to claim bonus'));
    } finally {
      setClaimingWelcome(false);
    }
  };

  // Redeem Promo Code
  const handleRedeemPromo = async () => {
    if (!promoCode.trim()) {
      toast.error('Please enter a promo code');
      return;
    }
    
    setPromoSubmitting(true);
    setRedeemResult(null); // Clear previous result
    const codeUsed = promoCode.trim().toUpperCase();
    
    try {
      const res = await rewardsApi.redeemPromo(codeUsed);
      
      if (res.data.success === true) {
        // SUCCESS: Set result and show toast
        const successMessage = res.data.message || 'Promo code redeemed successfully!';
        setRedeemResult({ status: 'success', message: successMessage });
        toast.success(successMessage);
        
        // Clear input and refetch history
        setPromoCode('');
        fetchPromoHistory();
      } else {
        // FAILURE (success === false): Set result and show toast
        const errorMessage = res.data.message || 'Unable to process promo code.';
        setRedeemResult({ status: 'error', message: errorMessage });
        toast.error(errorMessage);
      }
    } catch (err) {
      // HTTP ERROR (4xx/5xx): Set result and show toast
      const errorMessage = err.message || 'Unable to process promo code.';
      setRedeemResult({ status: 'error', message: errorMessage });
      toast.error(errorMessage);
    } finally {
      setPromoSubmitting(false);
    }
  };

  // Clear redeem result when user edits the promo code
  const handlePromoCodeChange = (e) => {
    setPromoCode(e.target.value);
    if (redeemResult) {
      setRedeemResult(null);
    }
  };

  // Fetch Promo History
  const fetchPromoHistory = useCallback(async () => {
    setPromoHistoryLoading(true);
    try {
      const res = await rewardsApi.getPromoHistory();
      setPromoHistory(res.data.history || res.data.redemptions || []);
    } catch (err) {
      console.error('Promo history error:', err);
      setPromoHistory([]);
    } finally {
      setPromoHistoryLoading(false);
    }
  }, []);

  // Fetch Referral Stats
  const fetchReferralStats = useCallback(async () => {
    setReferralLoading(true);
    try {
      const res = await referralsApi.getDetails();
      setReferralStats(res.data.stats || res.data);
    } catch (err) {
      console.error('Referral stats error:', err);
      setReferralStats({ total_referrals: 0, total_earned: 0, pending_rewards: 0 });
    } finally {
      setReferralLoading(false);
    }
  }, []);

  // Fetch Rewards List
  const fetchRewards = useCallback(async () => {
    setRewardsLoading(true);
    try {
      const res = await rewardsApi.getRewards();
      setRewards(res.data.rewards || []);
    } catch (err) {
      console.error('Rewards error:', err);
      setRewards([]);
    } finally {
      setRewardsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchWelcomeCredit();
    fetchReferralStats();
    fetchRewards();
  }, [fetchWelcomeCredit, fetchReferralStats, fetchRewards]);

  return (
    <div className="min-h-screen bg-[#0a0a0f] pb-24" data-testid="rewards-hub">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-[#0a0a0f]/95 backdrop-blur-xl border-b border-white/5">
        <div className="px-4 py-4 flex items-center gap-4">
          <button
            onClick={() => navigate(-1)}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-white" />
          </button>
          <div>
            <h1 className="text-xl font-bold text-white">Rewards Hub</h1>
            <p className="text-xs text-gray-500">Bonuses, promos & earnings</p>
          </div>
        </div>
      </header>

      <main className="px-4 py-6 space-y-6">
        {/* Welcome Bonus Section */}
        <section data-testid="welcome-bonus-section">
          <h2 className="text-sm font-semibold text-gray-400 mb-3 flex items-center gap-2">
            <Gift className="w-4 h-4" />
            Welcome Bonus
          </h2>
          
          {welcomeLoading ? (
            <div className="p-4 bg-white/[0.02] border border-white/5 rounded-2xl">
              <Skeleton className="h-6 w-40 mb-2" />
              <Skeleton className="h-4 w-60" />
            </div>
          ) : welcomeCredit?.has_credit ? (
            <div className="p-4 bg-gradient-to-r from-amber-500/20 to-orange-500/20 border border-amber-500/30 rounded-2xl">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-xl bg-amber-500/20 flex items-center justify-center">
                    <Sparkles className="w-6 h-6 text-amber-400" />
                  </div>
                  <div>
                    <h3 className="font-bold text-white">
                      ${welcomeCredit.amount?.toFixed(2) || '5.00'} Welcome Bonus
                    </h3>
                    <p className="text-sm text-amber-300/80">
                      Claim your free credits!
                    </p>
                  </div>
                </div>
                <button
                  onClick={handleClaimWelcome}
                  disabled={claimingWelcome}
                  className="px-4 py-2 bg-amber-500 hover:bg-amber-400 disabled:bg-amber-500/50 text-black font-semibold rounded-xl transition-all flex items-center gap-2"
                  data-testid="claim-welcome-btn"
                >
                  {claimingWelcome ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    'Claim'
                  )}
                </button>
              </div>
            </div>
          ) : (
            <div className="p-4 bg-white/[0.02] border border-white/5 rounded-2xl flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center">
                <CheckCircle className="w-5 h-5 text-emerald-400" />
              </div>
              <div>
                <p className="text-gray-400 text-sm">
                  {welcomeCredit?.claimed ? 'Welcome bonus already claimed!' : 'No welcome bonus available'}
                </p>
              </div>
            </div>
          )}
        </section>

        {/* Promo Code Section */}
        <section data-testid="promo-code-section">
          <h2 className="text-sm font-semibold text-gray-400 mb-3 flex items-center gap-2">
            <Ticket className="w-4 h-4" />
            Promo Code
          </h2>
          
          <div className="p-4 bg-white/[0.02] border border-white/5 rounded-2xl space-y-4">
            <div className="flex gap-2">
              <input
                type="text"
                value={promoCode}
                onChange={handlePromoCodeChange}
                placeholder="Enter promo code"
                className="flex-1 px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-violet-500/50 uppercase"
                data-testid="promo-code-input"
              />
              <button
                onClick={handleRedeemPromo}
                disabled={promoSubmitting || !promoCode.trim()}
                className="px-6 py-3 bg-violet-600 hover:bg-violet-500 disabled:bg-gray-700 disabled:text-gray-500 text-white font-semibold rounded-xl transition-all flex items-center gap-2"
                data-testid="redeem-promo-btn"
              >
                {promoSubmitting ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  'Apply'
                )}
              </button>
            </div>
            
            {/* Redeem Result Feedback */}
            {redeemResult && (
              <div 
                className={`flex items-start gap-3 p-3 rounded-xl ${
                  redeemResult.status === 'success' 
                    ? 'bg-emerald-500/10 border border-emerald-500/20' 
                    : 'bg-red-500/10 border border-red-500/20'
                }`}
                data-testid="redeem-result"
              >
                {redeemResult.status === 'success' ? (
                  <CheckCircle className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
                ) : (
                  <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
                )}
                <div>
                  <p className={`font-medium ${
                    redeemResult.status === 'success' ? 'text-emerald-400' : 'text-red-400'
                  }`}>
                    {redeemResult.status === 'success' ? 'Promo code redeemed' : 'Promo code not redeemed'}
                  </p>
                  <p className={`text-sm ${
                    redeemResult.status === 'success' ? 'text-emerald-400/80' : 'text-red-400/80'
                  }`}>
                    {redeemResult.message}
                  </p>
                </div>
              </div>
            )}
            
            <button
              onClick={() => {
                setShowPromoHistory(!showPromoHistory);
                if (!showPromoHistory && promoHistory.length === 0) {
                  fetchPromoHistory();
                }
              }}
              className="text-sm text-violet-400 hover:text-violet-300 flex items-center gap-1"
            >
              <History className="w-4 h-4" />
              {showPromoHistory ? 'Hide History' : 'View Promo History'}
            </button>
            
            {showPromoHistory && (
              <div className="pt-3 border-t border-white/5">
                {promoHistoryLoading ? (
                  <div className="space-y-2">
                    <Skeleton className="h-10 w-full" />
                    <Skeleton className="h-10 w-full" />
                  </div>
                ) : promoHistory.length === 0 ? (
                  <p className="text-gray-500 text-sm text-center py-4">
                    No promo codes redeemed yet
                  </p>
                ) : (
                  <div className="space-y-2 max-h-40 overflow-y-auto">
                    {promoHistory.map((item, idx) => (
                      <div key={idx} className="flex items-center justify-between p-2 bg-white/5 rounded-lg">
                        <div>
                          <p className="font-mono text-sm text-white">{item.code}</p>
                          <p className="text-xs text-gray-500">
                            {new Date(item.redeemed_at || item.created_at).toLocaleDateString()}
                          </p>
                        </div>
                        <span className="text-emerald-400 font-semibold">
                          +${item.amount?.toFixed(2) || item.credit_amount?.toFixed(2) || '0.00'}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </section>

        {/* Referral Rewards Summary */}
        <section data-testid="referral-rewards-section">
          <h2 className="text-sm font-semibold text-gray-400 mb-3 flex items-center gap-2">
            <Users className="w-4 h-4" />
            Referral Rewards
          </h2>
          
          {referralLoading ? (
            <div className="p-4 bg-white/[0.02] border border-white/5 rounded-2xl">
              <Skeleton className="h-16 w-full" />
            </div>
          ) : (
            <button
              onClick={() => navigate('/client/referrals')}
              className="w-full p-4 bg-gradient-to-r from-violet-600/20 via-fuchsia-600/20 to-emerald-500/20 border border-violet-500/20 rounded-2xl text-left hover:border-violet-500/40 transition-all group"
            >
              <div className="flex items-center justify-between">
                <div className="grid grid-cols-3 gap-4 flex-1">
                  <div>
                    <p className="text-xs text-gray-500">Total Referrals</p>
                    <p className="text-lg font-bold text-white">
                      {referralStats?.total_referrals || 0}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Total Earned</p>
                    <p className="text-lg font-bold text-emerald-400">
                      ${(referralStats?.total_earned || 0).toFixed(2)}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Pending</p>
                    <p className="text-lg font-bold text-amber-400">
                      ${(referralStats?.pending_rewards || 0).toFixed(2)}
                    </p>
                  </div>
                </div>
                <ChevronRight className="w-5 h-5 text-gray-500 group-hover:text-violet-400 group-hover:translate-x-1 transition-all" />
              </div>
            </button>
          )}
        </section>

        {/* Rewards List */}
        <section data-testid="rewards-list-section">
          <h2 className="text-sm font-semibold text-gray-400 mb-3 flex items-center gap-2">
            <Sparkles className="w-4 h-4" />
            Available Rewards
          </h2>
          
          {rewardsLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-20 w-full rounded-2xl" />
              <Skeleton className="h-20 w-full rounded-2xl" />
            </div>
          ) : rewards.length === 0 ? (
            <div className="p-8 bg-white/[0.02] border border-white/5 rounded-2xl text-center">
              <Gift className="w-10 h-10 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-500">No rewards available right now</p>
              <p className="text-xs text-gray-600 mt-1">Check back later for new offers!</p>
            </div>
          ) : (
            <div className="space-y-3">
              {rewards.map((reward, idx) => (
                <div 
                  key={idx}
                  className="p-4 bg-white/[0.02] border border-white/5 rounded-2xl flex items-center justify-between"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-violet-500/10 flex items-center justify-center">
                      <Gift className="w-5 h-5 text-violet-400" />
                    </div>
                    <div>
                      <p className="font-medium text-white">{reward.title || reward.name}</p>
                      <p className="text-xs text-gray-500">{reward.description}</p>
                    </div>
                  </div>
                  {reward.amount && (
                    <span className="text-emerald-400 font-bold">
                      ${reward.amount.toFixed(2)}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>
      </main>

      <ClientBottomNav active="profile" />
    </div>
  );
};

export default ClientRewards;

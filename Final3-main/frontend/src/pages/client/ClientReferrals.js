/**
 * ClientReferrals - NEW Premium Referral Page
 * Route: /client/referrals
 * 
 * DOES NOT use portal components - fully independent
 * 
 * Features:
 * - Hero gradient with copy link button
 * - Stats cards
 * - Progress timeline
 * - Earnings table
 * - Rules accordion
 */

import React, { useEffect, useState, useCallback } from 'react';
import { useAuth } from '../../context/AuthContext';
import { toast } from 'sonner';
import { 
  Users, Copy, Check, TrendingUp, Clock, UserPlus,
  ChevronDown, ChevronUp, Send, MessageCircle, Gift, Wallet,
  Info, Share2, CheckCircle2, RefreshCw
} from 'lucide-react';

// Centralized API
import { referralsApi, getErrorMessage, isServerUnavailable } from '../../api';
import { ClientBottomNav } from '../../features/shared/ClientBottomNav';
import { PageLoader } from '../../features/shared/LoadingStates';
import { ErrorState } from '../../features/shared/EmptyStates';

// Progress Steps
const PROGRESS_STEPS = [
  { key: 'joined', label: 'Joined', icon: UserPlus },
  { key: 'deposited', label: 'Deposited', icon: Wallet },
  { key: 'eligible', label: 'Eligible', icon: CheckCircle2 },
  { key: 'credited', label: 'Credited', icon: Gift },
];

// Status Badge Component
const StatusBadge = ({ status }) => {
  const statusConfig = {
    pending: { bg: 'bg-amber-500/10', text: 'text-amber-400', label: 'Pending' },
    credited: { bg: 'bg-emerald-500/10', text: 'text-emerald-400', label: 'Credited' },
    rejected: { bg: 'bg-red-500/10', text: 'text-red-400', label: 'Rejected' },
    active: { bg: 'bg-blue-500/10', text: 'text-blue-400', label: 'Active' },
    inactive: { bg: 'bg-gray-500/10', text: 'text-gray-400', label: 'Inactive' },
  };

  const config = statusConfig[status?.toLowerCase()] || statusConfig.pending;

  return (
    <span className={`inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-medium ${config.bg} ${config.text}`}>
      {config.label}
    </span>
  );
};

// Stat Card Component
const StatCard = ({ icon: Icon, value, label, color = 'violet' }) => {
  const colorClasses = {
    violet: 'text-violet-400 bg-violet-500/10',
    emerald: 'text-emerald-400 bg-emerald-500/10',
    amber: 'text-amber-400 bg-amber-500/10',
    blue: 'text-blue-400 bg-blue-500/10',
  };

  return (
    <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-4">
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center mb-3 ${colorClasses[color]}`}>
        <Icon className="w-5 h-5" />
      </div>
      <p className="text-2xl font-bold text-white">{value}</p>
      <p className="text-xs text-gray-500 mt-1">{label}</p>
    </div>
  );
};

// Referral Progress Component
const ReferralProgress = ({ referral }) => {
  const getStepStatus = (stepKey) => {
    const progress = referral?.progress || {};
    if (progress[stepKey]) return 'completed';
    
    const stepOrder = ['joined', 'deposited', 'eligible', 'credited'];
    const currentIndex = stepOrder.findIndex(s => !progress[s]);
    const stepIndex = stepOrder.indexOf(stepKey);
    
    if (stepIndex === currentIndex) return 'current';
    return 'pending';
  };

  return (
    <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-white">
            {referral?.masked_username || 'us***01'}
          </span>
          <StatusBadge status={referral?.status} />
        </div>
        <span className="text-xs text-gray-500">
          {referral?.joined_date || 'Recently'}
        </span>
      </div>
      
      {/* Progress Steps */}
      <div className="flex items-center justify-between relative">
        {/* Connection Line */}
        <div className="absolute top-4 left-6 right-6 h-0.5 bg-white/5 z-0" />
        
        {PROGRESS_STEPS.map((step) => {
          const status = getStepStatus(step.key);
          const StepIcon = step.icon;
          
          return (
            <div key={step.key} className="flex flex-col items-center z-10">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                status === 'completed' 
                  ? 'bg-emerald-500 text-white' 
                  : status === 'current'
                    ? 'bg-violet-500 text-white ring-4 ring-violet-500/20'
                    : 'bg-white/5 text-gray-500'
              }`}>
                {status === 'completed' ? (
                  <Check className="w-4 h-4" />
                ) : (
                  <StepIcon className="w-4 h-4" />
                )}
              </div>
              <span className={`text-[10px] mt-1.5 font-medium ${
                status === 'completed' ? 'text-emerald-400' : 
                status === 'current' ? 'text-violet-400' : 'text-gray-500'
              }`}>
                {step.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// Accordion Item Component
const AccordionItem = ({ title, children, defaultOpen = false }) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="border-b border-white/5 last:border-0">
      <button
        className="w-full flex items-center justify-between py-4 text-left focus:outline-none"
        onClick={() => setIsOpen(!isOpen)}
      >
        <span className="text-sm font-medium text-white">{title}</span>
        {isOpen ? (
          <ChevronUp className="w-5 h-5 text-gray-500" />
        ) : (
          <ChevronDown className="w-5 h-5 text-gray-500" />
        )}
      </button>
      {isOpen && (
        <div className="pb-4 text-sm text-gray-400 leading-relaxed animate-fadeIn">
          {children}
        </div>
      )}
    </div>
  );
};

// Main Component
const ClientReferrals = () => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [referralData, setReferralData] = useState(null);
  const [copied, setCopied] = useState(false);

  const fetchReferralData = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await referralsApi.getDetails();
      setReferralData(response.data);
    } catch (err) {
      const message = getErrorMessage(err, 'Failed to load referrals');
      
      if (isServerUnavailable(err)) {
        setError(message);
      } else {
        // Set demo data for fallback
        setReferralData({
          referral_code: user?.referral_code || 'DEMO2024',
          referral_link: `${window.location.origin}/register?ref=${user?.referral_code || 'DEMO2024'}`,
          stats: {
            total_referrals: 0,
            active_referrals: 0,
            total_earned: 0,
            pending_rewards: 0
          },
          referrals: [],
          earnings: []
        });
      }
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    fetchReferralData();
  }, [fetchReferralData]);

  const handleCopyLink = useCallback(() => {
    const link = referralData?.referral_link || 
      `${window.location.origin}/register?ref=${referralData?.referral_code || user?.referral_code || 'DEMO'}`;
    
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(link).then(() => {
        setCopied(true);
        toast.success('Referral link copied!');
        setTimeout(() => setCopied(false), 2500);
      }).catch(() => {
        toast.error('Could not copy link');
      });
    } else {
      // Fallback
      const textArea = document.createElement('textarea');
      textArea.value = link;
      document.body.appendChild(textArea);
      textArea.select();
      try {
        document.execCommand('copy');
        setCopied(true);
        toast.success('Referral link copied!');
        setTimeout(() => setCopied(false), 2500);
      } catch (err) {
        toast.error('Could not copy link');
      }
      document.body.removeChild(textArea);
    }
  }, [referralData, user]);

  const handleShareTelegram = () => {
    const link = referralData?.referral_link || 
      `${window.location.origin}/register?ref=${referralData?.referral_code}`;
    const text = encodeURIComponent(`Join me and get a bonus! Use my referral link: ${link}`);
    window.open(`https://t.me/share/url?url=${encodeURIComponent(link)}&text=${text}`, '_blank');
  };

  const handleShareWhatsApp = () => {
    const link = referralData?.referral_link || 
      `${window.location.origin}/register?ref=${referralData?.referral_code}`;
    const text = encodeURIComponent(`Join me and get a bonus! Use my referral link: ${link}`);
    window.open(`https://wa.me/?text=${text}`, '_blank');
  };

  // Safe number formatting
  const formatCurrency = (value) => {
    const num = typeof value === 'number' ? value : 0;
    return `$${num.toFixed(2)}`;
  };

  if (loading) {
    return <PageLoader message="Loading referrals..." />;
  }

  if (error && !referralData) {
    return (
      <div className="min-h-screen bg-[#0a0a0f] pb-20" data-testid="client-referrals">
        <header className="sticky top-0 z-40 bg-[#0a0a0f]/90 backdrop-blur-xl border-b border-white/5">
          <div className="px-4 py-4">
            <h1 className="text-xl font-bold text-white">Referrals</h1>
          </div>
        </header>
        <main className="px-4 py-6">
          <ErrorState 
            title="Could not load referrals" 
            description={error}
            onRetry={fetchReferralData} 
          />
        </main>
        <ClientBottomNav active="referrals" />
      </div>
    );
  }

  const stats = referralData?.stats || { total_referrals: 0, active_referrals: 0, total_earned: 0, pending_rewards: 0 };
  const referralCode = referralData?.referral_code || user?.referral_code || 'N/A';
  const referralLink = referralData?.referral_link || `${window.location.origin}/register?ref=${referralCode}`;
  const referrals = referralData?.referrals || [];
  const earnings = referralData?.earnings || [];

  return (
    <div className="min-h-screen bg-[#0a0a0f] pb-20" data-testid="client-referrals">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-[#0a0a0f]/90 backdrop-blur-xl border-b border-white/5">
        <div className="px-4 py-4 flex items-center justify-between">
          <h1 className="text-xl font-bold text-white">Referrals</h1>
          <button
            onClick={fetchReferralData}
            className="p-2 hover:bg-white/5 rounded-lg text-gray-400 hover:text-white transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </header>

      <main className="px-4 py-6 space-y-6">
        {/* Hero Section */}
        <section 
          className="relative overflow-hidden rounded-3xl"
          data-testid="referral-hero"
        >
          <div className="bg-gradient-to-br from-violet-600 via-fuchsia-600 to-emerald-500 p-5">
            <div className="text-center">
              {/* Primary headline */}
              <p className="text-amber-300 font-bold text-xl mb-1">
                💰 Earn 30% Cash Lifetime
              </p>
              
              {/* Secondary taglines */}
              <p className="text-white font-semibold text-base">Turn Your Network Into Earnings</p>
              <p className="text-white/80 text-sm mb-4">
                Earn up to 30% lifetime on every deposit your friends make
              </p>
              
              <button
                onClick={handleCopyLink}
                className="inline-flex items-center gap-2 px-6 py-3 bg-white text-violet-600 font-semibold rounded-xl hover:bg-white/95 hover:shadow-lg transition-all"
                data-testid="hero-copy-btn"
              >
                {copied ? <Check className="w-5 h-5" /> : <Copy className="w-5 h-5" />}
                {copied ? 'Copied!' : 'Copy Referral Link'}
              </button>
            </div>
          </div>
        </section>

        {/* Stats Section */}
        <section data-testid="referral-stats">
          <div className="grid grid-cols-2 gap-3">
            <StatCard 
              icon={Users} 
              value={stats.total_referrals} 
              label="Total Referrals" 
              color="violet"
            />
            <StatCard 
              icon={UserPlus} 
              value={stats.active_referrals} 
              label="Active Referrals" 
              color="blue"
            />
            <StatCard 
              icon={TrendingUp} 
              value={formatCurrency(stats.total_earned)} 
              label="Total Earned" 
              color="emerald"
            />
            <StatCard 
              icon={Clock} 
              value={formatCurrency(stats.pending_rewards)} 
              label="Pending Rewards" 
              color="amber"
            />
          </div>
        </section>

        {/* Referral Link Card */}
        <section data-testid="referral-link-card">
          <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-5">
            <h3 className="text-sm font-semibold text-white mb-4">Your Referral Link</h3>
            
            {/* Link Input */}
            <div className="flex gap-2 mb-4">
              <input
                type="text"
                value={referralLink}
                readOnly
                className="flex-1 px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-sm text-gray-300 font-mono truncate focus:outline-none"
                data-testid="referral-link-input"
              />
              <button
                onClick={handleCopyLink}
                className="px-4 py-3 bg-violet-600 text-white rounded-xl hover:bg-violet-500 transition-colors"
                data-testid="copy-link-btn"
              >
                {copied ? <Check className="w-5 h-5" /> : <Copy className="w-5 h-5" />}
              </button>
            </div>

            {/* Share Buttons */}
            <div className="flex gap-2">
              <button
                onClick={handleShareTelegram}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-[#229ED9]/20 text-[#229ED9] rounded-xl hover:bg-[#229ED9]/30 transition-colors text-sm font-medium"
                data-testid="share-telegram-btn"
              >
                <Send className="w-4 h-4" />
                Telegram
              </button>
              <button
                onClick={handleShareWhatsApp}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-[#25D366]/20 text-[#25D366] rounded-xl hover:bg-[#25D366]/30 transition-colors text-sm font-medium"
                data-testid="share-whatsapp-btn"
              >
                <MessageCircle className="w-4 h-4" />
                WhatsApp
              </button>
            </div>
          </div>
        </section>

        {/* Chatwoot Validation Notice - IMPORTANT */}
        <section data-testid="chatwoot-notice">
          <div className="bg-blue-500/10 border border-blue-500/20 rounded-2xl p-4">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-blue-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                <MessageCircle className="w-4 h-4 text-blue-400" />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-white mb-1">⚠️ Important: Referral Validation</h4>
                <p className="text-xs text-gray-400 leading-relaxed mb-2">
                  Your referral code is validated through our <strong className="text-blue-400">Messenger (Chatwoot)</strong>.
                </p>
                <p className="text-xs text-gray-400 leading-relaxed">
                  <strong className="text-white">How it works:</strong> Your friend must send your referral code 
                  <span className="font-mono bg-white/10 px-1 mx-1 rounded">{referralCode}</span> 
                  to our Messenger before or during registration to activate the referral bonus.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Referral Progress Section */}
        <section data-testid="referral-progress">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-white">Referral Progress</h3>
            <span className="text-xs text-gray-500">{referrals.length} referrals</span>
          </div>

          {referrals.length > 0 ? (
            <div className="space-y-3">
              {referrals.map((referral, idx) => (
                <ReferralProgress key={idx} referral={referral} />
              ))}
            </div>
          ) : (
            <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-8 text-center">
              <div className="w-16 h-16 bg-white/5 rounded-full flex items-center justify-center mx-auto mb-4">
                <Users className="w-8 h-8 text-gray-600" />
              </div>
              <p className="text-gray-400 text-sm mb-1">You haven't referred anyone yet.</p>
              <p className="text-gray-600 text-xs">Share your link to get started.</p>
            </div>
          )}
        </section>

        {/* Earnings Table */}
        {earnings.length > 0 && (
          <section data-testid="earnings-table">
            <h3 className="text-sm font-semibold text-white mb-4">Earnings History</h3>
            
            <div className="bg-white/[0.02] border border-white/5 rounded-2xl overflow-hidden">
              {/* Table Header */}
              <div className="grid grid-cols-4 gap-2 px-4 py-3 bg-white/[0.02] border-b border-white/5 text-xs font-medium text-gray-500 uppercase tracking-wide">
                <div>Friend</div>
                <div className="text-right">Deposit</div>
                <div className="text-right">Reward</div>
                <div className="text-center">Status</div>
              </div>
              
              {/* Table Body */}
              <div className="divide-y divide-white/5">
                {earnings.map((earning, idx) => (
                  <div 
                    key={idx} 
                    className="grid grid-cols-4 gap-2 px-4 py-3 items-center"
                  >
                    <div className="text-sm font-medium text-white truncate">{String(earning.friend || 'N/A')}</div>
                    <div className="text-sm text-gray-400 text-right">${earning.deposit_amount || 0}</div>
                    <div className="text-sm font-medium text-emerald-400 text-right">
                      ${(earning.reward_earned || 0).toFixed(2)}
                    </div>
                    <div className="text-center">
                      <StatusBadge status={earning.status} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </section>
        )}

        {/* Referral Rules Accordion */}
        <section data-testid="referral-rules">
          <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-5">
            <div className="flex items-center gap-2 mb-4">
              <Info className="w-5 h-5 text-violet-400" />
              <h3 className="text-sm font-semibold text-white">Referral Rules</h3>
            </div>

            <AccordionItem title="When are rewards credited?" defaultOpen>
              <p>
                Rewards are credited to your wallet once your referred friend completes their first deposit 
                and the deposit is approved by our team. This typically happens within 24 hours.
              </p>
            </AccordionItem>

            <AccordionItem title="Bonus limits">
              <ul className="list-disc list-inside space-y-1">
                <li>Standard referral bonus: 10% of friend's first deposit</li>
                <li>Maximum bonus per referral: $500</li>
                <li>No limit on the number of referrals</li>
                <li>Bonuses are subject to 1x playthrough requirement</li>
              </ul>
            </AccordionItem>

            <AccordionItem title="Abuse prevention">
              <p className="mb-2">
                To ensure fairness, the following rules apply:
              </p>
              <ul className="list-disc list-inside space-y-1">
                <li>Self-referrals are not allowed</li>
                <li>Multiple accounts per person are prohibited</li>
                <li>Suspicious activity may result in bonus forfeiture</li>
                <li>We reserve the right to modify or cancel bonuses</li>
              </ul>
            </AccordionItem>
          </div>
        </section>
      </main>

      <ClientBottomNav active="referrals" />
    </div>
  );
};

export default ClientReferrals;

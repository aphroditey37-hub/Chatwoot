/**
 * ClientWallet - Enhanced Wallet Page
 * Route: /client/wallet
 * 
 * Features:
 * - Balance card with Add Funds + Withdraw buttons
 * - Bonus & Withdrawal Info section (collapsible)
 * - Tabbed view: Transactions | Deposits | Ledger
 * - Transaction list with status badges
 * - Expandable transaction details
 */

import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { toast } from 'sonner';
import { 
  Plus, ArrowUpRight, ArrowDownLeft, Clock, 
  ChevronRight, ChevronDown, RefreshCw, Check, X, AlertCircle,
  Info, Ban, Calendar, Loader2, Gift, Wallet, BookOpen, TrendingUp
} from 'lucide-react';

// Centralized API
import { walletApi, transactionsApi, getErrorMessage, isServerUnavailable } from '../../api';
import http from '../../api/http';
import { ClientBottomNav } from '../../features/shared/ClientBottomNav';
import { PageLoader } from '../../features/shared/LoadingStates';
import { EmptyState, ErrorState } from '../../features/shared/EmptyStates';

// Skeleton Loader
const Skeleton = ({ className = '' }) => (
  <div className={`bg-white/5 animate-pulse rounded ${className}`} />
);

const ClientWallet = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [walletData, setWalletData] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [filter, setFilter] = useState('all');
  const [expandedTx, setExpandedTx] = useState(null);
  
  // Tab state
  const [activeTab, setActiveTab] = useState(searchParams.get('tab') || 'transactions');
  
  // Bonus Info state
  const [bonusInfoExpanded, setBonusInfoExpanded] = useState(false);
  const [bonusLoading, setBonusLoading] = useState(false);
  const [breakdown, setBreakdown] = useState(null);
  const [bonusProgress, setBonusProgress] = useState(null);
  const [cashoutPreview, setCashoutPreview] = useState(null);
  const [bonusError, setBonusError] = useState(null);
  
  // Deposits state
  const [deposits, setDeposits] = useState([]);
  const [depositsLoading, setDepositsLoading] = useState(false);
  
  // Ledger state
  const [ledger, setLedger] = useState([]);
  const [ledgerLoading, setLedgerLoading] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const [walletRes, transactionsRes] = await Promise.all([
        walletApi.getBalance(),
        transactionsApi.getEnhanced({ limit: 50 }).catch(() => ({ data: { transactions: [] } }))
      ]);
      
      setWalletData(walletRes.data);
      setTransactions(transactionsRes.data.transactions || []);
    } catch (err) {
      const message = getErrorMessage(err, 'Failed to load wallet');
      setError(message);
      
      if (!isServerUnavailable(err)) {
        setWalletData({
          wallet_balance: 0,
          play_credits: 0,
          bonus_balance: 0,
          cash_balance: 0
        });
      }
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch Bonus Info
  const fetchBonusInfo = useCallback(async () => {
    setBonusLoading(true);
    setBonusError(null);
    
    try {
      const [breakdownRes, progressRes, cashoutRes] = await Promise.allSettled([
        walletApi.getBreakdown(),
        walletApi.getBonusProgress(),
        walletApi.getCashoutPreview()
      ]);
      
      if (breakdownRes.status === 'fulfilled') setBreakdown(breakdownRes.value.data);
      if (progressRes.status === 'fulfilled') setBonusProgress(progressRes.value.data);
      if (cashoutRes.status === 'fulfilled') setCashoutPreview(cashoutRes.value.data);
    } catch (err) {
      setBonusError(getErrorMessage(err, 'Failed to load bonus info'));
    } finally {
      setBonusLoading(false);
    }
  }, []);

  // Fetch Deposits
  const fetchDeposits = useCallback(async () => {
    setDepositsLoading(true);
    try {
      const res = await walletApi.getLoadHistory();
      setDeposits(res.data.history || res.data.requests || []);
    } catch (err) {
      console.error('Deposits fetch error:', err);
      setDeposits([]);
    } finally {
      setDepositsLoading(false);
    }
  }, []);

  // Fetch Ledger
  const fetchLedger = useCallback(async () => {
    setLedgerLoading(true);
    try {
      const res = await walletApi.getLedger();
      setLedger(res.data.entries || res.data.ledger || []);
    } catch (err) {
      console.error('Ledger fetch error:', err);
      setLedger([]);
    } finally {
      setLedgerLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Handle tab changes
  useEffect(() => {
    if (activeTab === 'deposits' && deposits.length === 0 && !depositsLoading) {
      fetchDeposits();
    }
    if (activeTab === 'ledger' && ledger.length === 0 && !ledgerLoading) {
      fetchLedger();
    }
  }, [activeTab, deposits.length, ledger.length, depositsLoading, ledgerLoading, fetchDeposits, fetchLedger]);

  // Handle bonus info expansion
  useEffect(() => {
    if (bonusInfoExpanded && !breakdown && !bonusLoading) {
      fetchBonusInfo();
    }
  }, [bonusInfoExpanded, breakdown, bonusLoading, fetchBonusInfo]);

  const handleTabChange = (tab) => {
    setActiveTab(tab);
    setSearchParams({ tab });
  };

  const filteredTransactions = transactions.filter(tx => {
    if (filter === 'all') return true;
    if (filter === 'deposits') return tx.type === 'IN' || tx.order_type?.includes('load') || tx.order_type?.includes('deposit');
    if (filter === 'withdrawals') return tx.type === 'OUT' || tx.order_type?.includes('withdrawal');
    if (filter === 'pending') return ['pending', 'pending_approval', 'pending_review', 'initiated', 'awaiting_payment_proof'].includes(tx.status);
    return true;
  });

  const getStatusIcon = (status) => {
    switch (status) {
      case 'approved':
      case 'completed':
      case 'credited':
        return <Check className="w-4 h-4 text-emerald-400" />;
      case 'pending':
      case 'pending_approval':
      case 'pending_review':
      case 'initiated':
      case 'awaiting_payment_proof':
        return <Clock className="w-4 h-4 text-amber-400" />;
      case 'failed':
      case 'rejected':
      case 'cancelled':
        return <X className="w-4 h-4 text-red-400" />;
      default:
        return <AlertCircle className="w-4 h-4 text-gray-400" />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'approved':
      case 'completed':
      case 'credited':
        return 'text-emerald-400 bg-emerald-500/10';
      case 'pending':
      case 'pending_approval':
      case 'pending_review':
      case 'initiated':
      case 'awaiting_payment_proof':
        return 'text-amber-400 bg-amber-500/10';
      case 'failed':
      case 'rejected':
      case 'cancelled':
        return 'text-red-400 bg-red-500/10';
      default:
        return 'text-gray-400 bg-gray-500/10';
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const toggleExpand = (txId) => {
    setExpandedTx(expandedTx === txId ? null : txId);
  };

  if (loading) {
    return <PageLoader message="Loading wallet..." />;
  }

  if (error && !walletData) {
    return (
      <div className="min-h-screen bg-[#0a0a0f] pb-20" data-testid="client-wallet">
        <header className="sticky top-0 z-40 bg-[#0a0a0f]/90 backdrop-blur-xl border-b border-white/5">
          <div className="px-4 py-4">
            <h1 className="text-xl font-bold text-white">Wallet</h1>
          </div>
        </header>
        <main className="px-4 py-6">
          <ErrorState 
            title="Could not load wallet" 
            description={error}
            onRetry={fetchData} 
          />
        </main>
        <ClientBottomNav active="wallet" />
      </div>
    );
  }

  const totalBalance = walletData?.wallet_balance || walletData?.real_balance || 0;
  const pendingAmount = transactions
    .filter(t => ['pending', 'pending_approval', 'pending_review', 'initiated', 'awaiting_payment_proof'].includes(t.status))
    .reduce((sum, t) => sum + (t.amount || 0), 0);

  return (
    <div className="min-h-screen bg-[#0a0a0f] pb-20" data-testid="client-wallet">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-[#0a0a0f]/90 backdrop-blur-xl border-b border-white/5">
        <div className="px-4 py-4">
          <h1 className="text-xl font-bold text-white">Wallet</h1>
        </div>
      </header>

      <main className="px-4 py-6 space-y-5">
        {/* Balance Card */}
        <div className="relative overflow-hidden p-6 bg-gradient-to-br from-violet-900/40 via-fuchsia-900/30 to-violet-900/40 border border-violet-500/20 rounded-3xl">
          <div className="absolute inset-0 opacity-5">
            <div className="absolute top-0 right-0 w-40 h-40 bg-violet-500 rounded-full blur-3xl" />
          </div>
          
          <div className="relative">
            <p className="text-sm text-gray-400 mb-1">Available Balance</p>
            <h2 className="text-4xl font-bold text-white mb-6">
              ${totalBalance.toFixed(2)}
            </h2>

            {/* Balance Breakdown */}
            <div className="grid grid-cols-3 gap-3 mb-6">
              <div className="bg-white/5 rounded-xl p-3 text-center">
                <p className="text-xs text-gray-500 mb-1">Cash</p>
                <p className="text-sm font-semibold text-emerald-400">
                  ${(walletData?.cash_balance || 0).toFixed(2)}
                </p>
              </div>
              <div className="bg-white/5 rounded-xl p-3 text-center">
                <p className="text-xs text-gray-500 mb-1">Play Credits</p>
                <p className="text-sm font-semibold text-violet-400">
                  ${(walletData?.play_credits || 0).toFixed(2)}
                </p>
              </div>
              <div className="bg-white/5 rounded-xl p-3 text-center">
                <p className="text-xs text-gray-500 mb-1">Bonus</p>
                <p className="text-sm font-semibold text-amber-400">
                  ${(walletData?.bonus_balance || 0).toFixed(2)}
                </p>
              </div>
            </div>

            {/* Summary Row */}
            <div className="flex items-center justify-between mb-6 px-2">
              <div>
                <p className="text-xs text-gray-500">Withdrawable</p>
                <p className="font-semibold text-emerald-400">
                  ${(walletData?.withdrawable || walletData?.cash_balance || 0).toFixed(2)}
                </p>
              </div>
              <div className="text-right">
                <p className="text-xs text-gray-500">Pending</p>
                <p className="font-semibold text-amber-400">
                  ${pendingAmount.toFixed(2)}
                </p>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-3">
              <button
                onClick={() => navigate('/client/wallet/add')}
                className="flex-1 flex items-center justify-center gap-2 py-3.5 bg-gradient-to-r from-emerald-600 to-emerald-500 hover:from-emerald-500 hover:to-emerald-400 text-white font-semibold rounded-xl transition-all shadow-lg shadow-emerald-500/20"
                data-testid="add-funds-btn"
              >
                <Plus className="w-5 h-5" />
                Add Funds
              </button>
              <button
                onClick={() => navigate('/client/wallet/withdraw')}
                className="flex-1 flex items-center justify-center gap-2 py-3.5 bg-white/10 hover:bg-white/15 text-white font-semibold rounded-xl transition-all border border-white/5"
                data-testid="withdraw-btn"
              >
                <ArrowUpRight className="w-5 h-5" />
                Withdraw
              </button>
            </div>
          </div>
        </div>

        {/* Bonus & Withdrawal Info (Collapsible) */}
        <div className="bg-white/[0.02] border border-white/5 rounded-2xl overflow-hidden">
          <button
            onClick={() => setBonusInfoExpanded(!bonusInfoExpanded)}
            className="w-full px-4 py-3 flex items-center justify-between hover:bg-white/[0.02] transition-colors"
            data-testid="bonus-info-toggle"
          >
            <div className="flex items-center gap-2">
              <Gift className="w-4 h-4 text-violet-400" />
              <span className="font-medium text-white text-sm">Bonus & Withdrawal Info</span>
            </div>
            <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${bonusInfoExpanded ? 'rotate-180' : ''}`} />
          </button>
          
          {bonusInfoExpanded && (
            <div className="px-4 pb-4 border-t border-white/5 pt-3 space-y-4">
              {bonusLoading ? (
                <div className="space-y-3">
                  <Skeleton className="h-16 w-full" />
                  <Skeleton className="h-12 w-full" />
                </div>
              ) : bonusError ? (
                <div className="flex items-center justify-between p-3 bg-red-500/10 rounded-xl">
                  <p className="text-red-400 text-sm">{bonusError}</p>
                  <button 
                    onClick={fetchBonusInfo}
                    className="text-red-400 hover:text-red-300"
                  >
                    <RefreshCw className="w-4 h-4" />
                  </button>
                </div>
              ) : (
                <>
                  {/* Breakdown */}
                  {breakdown && (
                    <div className="grid grid-cols-2 gap-2">
                      <div className="p-3 bg-white/5 rounded-xl">
                        <p className="text-xs text-gray-500">Locked Balance</p>
                        <p className="text-sm font-semibold text-amber-400">
                          ${(breakdown.locked_balance || 0).toFixed(2)}
                        </p>
                      </div>
                      <div className="p-3 bg-white/5 rounded-xl">
                        <p className="text-xs text-gray-500">Withdrawable Now</p>
                        <p className="text-sm font-semibold text-emerald-400">
                          ${(breakdown.withdrawable || breakdown.available_to_withdraw || 0).toFixed(2)}
                        </p>
                      </div>
                    </div>
                  )}
                  
                  {/* Bonus Progress */}
                  {bonusProgress && bonusProgress.total_required > 0 && (
                    <div className="p-3 bg-white/5 rounded-xl">
                      <div className="flex items-center justify-between mb-2">
                        <p className="text-xs text-gray-500">Bonus Progress</p>
                        <p className="text-xs text-violet-400">
                          {Math.round((bonusProgress.current_progress / bonusProgress.total_required) * 100)}%
                        </p>
                      </div>
                      <div className="w-full h-2 bg-white/10 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-gradient-to-r from-violet-500 to-fuchsia-500 rounded-full transition-all"
                          style={{ width: `${Math.min(100, (bonusProgress.current_progress / bonusProgress.total_required) * 100)}%` }}
                        />
                      </div>
                      <p className="text-xs text-gray-500 mt-1">
                        ${bonusProgress.current_progress?.toFixed(2)} / ${bonusProgress.total_required?.toFixed(2)} wagered
                      </p>
                    </div>
                  )}
                  
                  {/* Cashout Preview */}
                  {cashoutPreview && (
                    <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl">
                      <p className="text-xs text-gray-400 mb-1">If you withdraw now:</p>
                      <p className="text-lg font-bold text-emerald-400">
                        You receive: ${(cashoutPreview.net_payout || cashoutPreview.receive_amount || 0).toFixed(2)}
                      </p>
                      {(cashoutPreview.forfeited_amount || cashoutPreview.bonus_forfeited) > 0 && (
                        <p className="text-xs text-amber-400 mt-1">
                          ⚠️ Locked/bonus forfeited: ${(cashoutPreview.forfeited_amount || cashoutPreview.bonus_forfeited || 0).toFixed(2)}
                        </p>
                      )}
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </div>

        {/* Tab Navigation */}
        <div className="flex bg-white/[0.02] rounded-xl p-1 gap-1">
          {[
            { id: 'transactions', label: 'Transactions', icon: ArrowDownLeft },
            { id: 'deposits', label: 'Deposits', icon: Wallet },
            { id: 'ledger', label: 'Ledger', icon: BookOpen },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => handleTabChange(tab.id)}
              className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                activeTab === tab.id
                  ? 'bg-violet-500/20 text-violet-400'
                  : 'text-gray-400 hover:text-white hover:bg-white/5'
              }`}
              data-testid={`tab-${tab.id}`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Transactions Tab */}
        {activeTab === 'transactions' && (
          <div className="space-y-4">
            {/* Filters */}
            <div className="flex gap-2 overflow-x-auto pb-2">
              {[
                { id: 'all', label: 'All' },
                { id: 'deposits', label: 'Deposits' },
                { id: 'withdrawals', label: 'Withdrawals' },
                { id: 'pending', label: 'Pending' },
              ].map(f => (
                <button
                  key={f.id}
                  onClick={() => setFilter(f.id)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-all ${
                    filter === f.id
                      ? 'bg-violet-500/20 text-violet-400'
                      : 'bg-white/5 text-gray-400 hover:text-white'
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>

            {/* Transaction List */}
            {filteredTransactions.length === 0 ? (
              <EmptyState 
                icon={ArrowDownLeft}
                title="No transactions yet"
                description="Your transactions will appear here"
              />
            ) : (
              <div className="space-y-2">
                {filteredTransactions.map(tx => (
                  <div 
                    key={tx.order_id || tx.id}
                    className="bg-white/[0.02] border border-white/5 rounded-xl overflow-hidden"
                  >
                    <button
                      onClick={() => toggleExpand(tx.order_id || tx.id)}
                      className="w-full p-4 flex items-center justify-between text-left"
                    >
                      <div className="flex items-center gap-3">
                        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                          tx.type === 'IN' || tx.order_type?.includes('load') || tx.order_type?.includes('deposit')
                            ? 'bg-emerald-500/10'
                            : 'bg-red-500/10'
                        }`}>
                          {tx.type === 'IN' || tx.order_type?.includes('load') || tx.order_type?.includes('deposit') ? (
                            <ArrowDownLeft className="w-5 h-5 text-emerald-400" />
                          ) : (
                            <ArrowUpRight className="w-5 h-5 text-red-400" />
                          )}
                        </div>
                        <div>
                          <p className="font-medium text-white text-sm">
                            {tx.order_type?.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) || tx.type || 'Transaction'}
                          </p>
                          <p className="text-xs text-gray-500">{formatDate(tx.created_at)}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="text-right">
                          <p className={`font-semibold ${
                            tx.type === 'IN' || tx.order_type?.includes('load') || tx.order_type?.includes('deposit')
                              ? 'text-emerald-400'
                              : 'text-red-400'
                          }`}>
                            {tx.type === 'IN' || tx.order_type?.includes('load') || tx.order_type?.includes('deposit') ? '+' : '-'}
                            ${(tx.amount || 0).toFixed(2)}
                          </p>
                          <span className={`text-xs px-2 py-0.5 rounded-lg ${getStatusColor(tx.status)}`}>
                            {tx.status?.replace(/_/g, ' ')}
                          </span>
                        </div>
                        <ChevronDown className={`w-4 h-4 text-gray-500 transition-transform ${expandedTx === (tx.order_id || tx.id) ? 'rotate-180' : ''}`} />
                      </div>
                    </button>
                    
                    {expandedTx === (tx.order_id || tx.id) && (
                      <div className="px-4 pb-4 pt-2 border-t border-white/5 space-y-2 text-sm">
                        {tx.order_id && (
                          <div className="flex justify-between">
                            <span className="text-gray-500">Order ID</span>
                            <span className="text-gray-300 font-mono text-xs">{tx.order_id.slice(0, 8)}...</span>
                          </div>
                        )}
                        {tx.game_name && (
                          <div className="flex justify-between">
                            <span className="text-gray-500">Game</span>
                            <span className="text-gray-300">{tx.game_name}</span>
                          </div>
                        )}
                        {tx.payment_method && (
                          <div className="flex justify-between">
                            <span className="text-gray-500">Method</span>
                            <span className="text-gray-300">{tx.payment_method}</span>
                          </div>
                        )}
                        {tx.notes && (
                          <div className="flex justify-between">
                            <span className="text-gray-500">Notes</span>
                            <span className="text-gray-300 text-right max-w-[60%]">{tx.notes}</span>
                          </div>
                        )}
                        <button
                          onClick={() => navigate(`/client/wallet/transaction/${tx.order_id}`)}
                          className="w-full mt-2 py-2 text-violet-400 hover:text-violet-300 text-sm flex items-center justify-center gap-1"
                        >
                          View Full Details
                          <ChevronRight className="w-4 h-4" />
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Deposits Tab */}
        {activeTab === 'deposits' && (
          <div className="space-y-3">
            {depositsLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-16 w-full rounded-xl" />
                <Skeleton className="h-16 w-full rounded-xl" />
                <Skeleton className="h-16 w-full rounded-xl" />
              </div>
            ) : deposits.length === 0 ? (
              <EmptyState 
                icon={Wallet}
                title="No deposits yet"
                description="Your deposit history will appear here"
              />
            ) : (
              deposits.map((dep, idx) => (
                <div key={dep.request_id || idx} className="p-4 bg-white/[0.02] border border-white/5 rounded-xl">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      {getStatusIcon(dep.status)}
                      <div>
                        <p className="font-medium text-white">${(dep.amount || 0).toFixed(2)}</p>
                        <p className="text-xs text-gray-500">{dep.payment_method || 'Deposit'}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <span className={`text-xs px-2 py-0.5 rounded-lg ${getStatusColor(dep.status)}`}>
                        {dep.status?.replace(/_/g, ' ')}
                      </span>
                      <p className="text-xs text-gray-500 mt-1">{formatDate(dep.created_at)}</p>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {/* Ledger Tab */}
        {activeTab === 'ledger' && (
          <div className="space-y-3">
            <p className="text-xs text-gray-500 px-1">Advanced financial history</p>
            
            {ledgerLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-12 w-full rounded-xl" />
                <Skeleton className="h-12 w-full rounded-xl" />
                <Skeleton className="h-12 w-full rounded-xl" />
              </div>
            ) : ledger.length === 0 ? (
              <EmptyState 
                icon={BookOpen}
                title="No ledger entries"
                description="Your financial ledger will appear here"
              />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-gray-500 text-xs">
                      <th className="pb-2 font-medium">Date</th>
                      <th className="pb-2 font-medium">Type</th>
                      <th className="pb-2 font-medium text-right">Amount</th>
                      <th className="pb-2 font-medium text-right">Balance</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {ledger.map((entry, idx) => (
                      <tr key={entry.ledger_id || idx} className="hover:bg-white/[0.02]">
                        <td className="py-3 text-gray-400 text-xs">
                          {formatDate(entry.created_at)}
                        </td>
                        <td className="py-3">
                          <span className={`text-xs px-2 py-0.5 rounded ${
                            entry.type === 'credit' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'
                          }`}>
                            {entry.type || entry.transaction_type}
                          </span>
                        </td>
                        <td className={`py-3 text-right font-medium ${
                          entry.type === 'credit' ? 'text-emerald-400' : 'text-red-400'
                        }`}>
                          {entry.type === 'credit' ? '+' : '-'}${Math.abs(entry.amount || 0).toFixed(2)}
                        </td>
                        <td className="py-3 text-right text-white">
                          ${(entry.balance_after || 0).toFixed(2)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </main>

      <ClientBottomNav active="wallet" />
    </div>
  );
};

export default ClientWallet;

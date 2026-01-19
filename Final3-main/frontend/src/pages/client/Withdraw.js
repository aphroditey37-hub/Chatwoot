/**
 * Withdraw - Migrated to new API layer
 * Route: /client/wallet/withdraw
 * 
 * Features:
 * - Amount input
 * - Withdrawal method selection
 * - Account details
 * - Warning about approval required
 * - Success state with pending status
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { 
  DollarSign, Building2, CheckCircle, Loader2, AlertCircle,
  ArrowLeft, Info
} from 'lucide-react';

// Centralized API
import http, { getErrorMessage, isServerUnavailable } from '../../api/http';
import { PageLoader } from '../../features/shared/LoadingStates';

const withdrawalMethods = [
  { id: 'gcash', name: 'GCash' },
  { id: 'paymaya', name: 'PayMaya' },
  { id: 'bank', name: 'Bank Transfer' },
];

const Withdraw = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [step, setStep] = useState(1);
  const [walletData, setWalletData] = useState(null);
  const [amount, setAmount] = useState('');
  const [method, setMethod] = useState('');
  const [accountNumber, setAccountNumber] = useState('');
  const [accountName, setAccountName] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [orderId, setOrderId] = useState(null);
  const [error, setError] = useState(null);

  const fetchWallet = useCallback(async () => {
    setLoading(true);
    try {
      const response = await http.get('/wallet/balance');
      setWalletData(response.data);
    } catch (err) {
      const message = getErrorMessage(err, 'Failed to load wallet');
      toast.error(message);
      // Set default
      setWalletData({ cash_balance: 0 });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchWallet();
  }, [fetchWallet]);

  const cashBalance = walletData?.cash_balance || 0;

  const handleSubmit = async () => {
    if (!amount || parseFloat(amount) <= 0) {
      toast.error('Please enter a valid amount');
      return;
    }
    if (parseFloat(amount) > cashBalance) {
      toast.error('Insufficient withdrawable balance');
      return;
    }
    if (!method || !accountNumber || !accountName) {
      toast.error('Please fill in all fields');
      return;
    }

    setSubmitting(true);
    setError(null);
    
    try {
      const response = await http.post('/withdrawal/wallet', {
        amount: parseFloat(amount),
        withdrawal_method: method.toUpperCase(),
        account_number: accountNumber,
        account_name: accountName
      });

      if (response.data.success) {
        setOrderId(response.data.order_id || response.data.withdrawal_id);
        setSuccess(true);
        toast.success('Withdrawal request submitted!');
      } else {
        throw new Error(response.data.message || 'Withdrawal failed');
      }
    } catch (err) {
      const message = getErrorMessage(err, 'Failed to submit request');
      setError(message);
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return <PageLoader message="Loading wallet..." />;
  }

  if (success) {
    return (
      <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center p-4">
        <div className="max-w-sm w-full text-center">
          <div className="w-20 h-20 bg-emerald-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
            <CheckCircle className="w-10 h-10 text-emerald-400" />
          </div>
          <h2 className="text-2xl font-bold text-white mb-2">Request Submitted!</h2>
          <p className="text-gray-400 mb-4">
            Your withdrawal request for ${parseFloat(amount).toFixed(2)} has been submitted.
          </p>
          
          {/* Pending approval info */}
          <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-xl mb-6">
            <div className="flex items-center gap-2 mb-2">
              <Info className="w-5 h-5 text-amber-400" />
              <p className="text-amber-400 font-medium text-sm">Pending Approval</p>
            </div>
            <p className="text-xs text-amber-400/70">
              Balance has been deducted. If the withdrawal is rejected, it will be automatically refunded.
            </p>
            {orderId && (
              <p className="text-xs text-gray-500 mt-2 font-mono">
                Order ID: {orderId.slice(0, 8)}...
              </p>
            )}
          </div>
          
          <button
            onClick={() => navigate('/client/wallet')}
            className="w-full py-3.5 bg-violet-600 hover:bg-violet-500 text-white font-semibold rounded-xl transition-all"
            data-testid="back-to-wallet-btn"
          >
            Back to Wallet
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0a0f]" data-testid="withdraw-page">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-[#0a0a0f]/90 backdrop-blur-xl border-b border-white/5">
        <div className="px-4 py-4 flex items-center gap-4">
          <button
            onClick={() => navigate('/client/wallet')}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-white" />
          </button>
          <h1 className="text-xl font-bold text-white">Withdraw</h1>
        </div>
      </header>

      <main className="px-4 py-6 max-w-lg mx-auto">
        {/* Available Balance */}
        <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-2xl mb-6">
          <p className="text-xs text-emerald-400 mb-1">Withdrawable Balance</p>
          <p className="text-2xl font-bold text-white">${cashBalance.toFixed(2)}</p>
          <p className="text-xs text-gray-500 mt-1">Only cash balance can be withdrawn</p>
        </div>

        {/* Approval Warning */}
        <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-xl mb-6">
          <div className="flex items-center gap-2 mb-1">
            <AlertCircle className="w-5 h-5 text-amber-400" />
            <p className="text-amber-400 font-medium text-sm">Approval Required</p>
          </div>
          <p className="text-xs text-amber-400/70">
            Withdrawals require admin approval. Balance will be deducted immediately and refunded if rejected.
          </p>
        </div>

        {/* Step Indicator */}
        <div className="flex items-center justify-center gap-2 mb-8">
          {[1, 2].map(s => (
            <div
              key={s}
              className={`w-2.5 h-2.5 rounded-full transition-all ${
                s === step ? 'w-8 bg-violet-500' : s < step ? 'bg-emerald-500' : 'bg-white/10'
              }`}
            />
          ))}
        </div>

        {/* Step 1: Amount & Method */}
        {step === 1 && (
          <div className="space-y-6 animate-fadeIn">
            <div className="text-center mb-6">
              <h2 className="text-xl font-bold text-white mb-2">Withdrawal Details</h2>
              <p className="text-gray-400 text-sm">Enter amount and select method</p>
            </div>

            {/* Amount Input */}
            <div>
              <label className="text-sm text-gray-400 mb-2 block">Amount</label>
              <div className="relative">
                <DollarSign className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                <input
                  type="number"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  placeholder="0.00"
                  max={cashBalance}
                  className="w-full pl-11 pr-4 py-3.5 text-lg font-bold bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-600 focus:outline-none focus:border-violet-500/50"
                  data-testid="amount-input"
                />
              </div>
              {amount && parseFloat(amount) > cashBalance && (
                <p className="text-xs text-red-400 mt-2 flex items-center gap-1">
                  <AlertCircle className="w-3 h-3" />
                  Exceeds withdrawable balance
                </p>
              )}
            </div>

            {/* Method Selection */}
            <div>
              <label className="text-sm text-gray-400 mb-2 block">Withdrawal Method</label>
              <div className="space-y-2">
                {withdrawalMethods.map(m => (
                  <button
                    key={m.id}
                    onClick={() => setMethod(m.id)}
                    className={`w-full p-4 rounded-xl border transition-all flex items-center gap-3 ${
                      method === m.id
                        ? 'bg-violet-500/10 border-violet-500/50'
                        : 'bg-white/[0.02] border-white/5 hover:border-white/20'
                    }`}
                    data-testid={`method-${m.id}`}
                  >
                    <Building2 className="w-5 h-5 text-gray-400" />
                    <span className="font-medium text-white">{m.name}</span>
                    {method === m.id && (
                      <CheckCircle className="w-5 h-5 text-violet-400 ml-auto" />
                    )}
                  </button>
                ))}
              </div>
            </div>

            <button
              onClick={() => amount && parseFloat(amount) > 0 && parseFloat(amount) <= cashBalance && method && setStep(2)}
              disabled={!amount || parseFloat(amount) <= 0 || parseFloat(amount) > cashBalance || !method}
              className="w-full py-4 bg-violet-600 hover:bg-violet-500 disabled:bg-gray-700 disabled:text-gray-500 text-white font-semibold rounded-xl transition-all"
              data-testid="continue-btn"
            >
              Continue
            </button>
          </div>
        )}

        {/* Step 2: Account Details */}
        {step === 2 && (
          <div className="space-y-6 animate-fadeIn">
            <div className="text-center mb-6">
              <h2 className="text-xl font-bold text-white mb-2">Account Details</h2>
              <p className="text-gray-400 text-sm">Where should we send the funds?</p>
            </div>

            {/* Summary */}
            <div className="p-4 bg-white/[0.02] border border-white/5 rounded-xl">
              <div className="flex justify-between mb-2">
                <span className="text-gray-400">Amount</span>
                <span className="font-bold text-white">${parseFloat(amount).toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Method</span>
                <span className="text-white capitalize">{method}</span>
              </div>
            </div>

            {/* Account Number */}
            <div>
              <label className="text-sm text-gray-400 mb-2 block">
                {method === 'bank' ? 'Account Number' : 'Mobile Number'}
              </label>
              <input
                type="text"
                value={accountNumber}
                onChange={(e) => setAccountNumber(e.target.value)}
                placeholder={method === 'bank' ? '1234567890' : '09XX XXX XXXX'}
                className="w-full px-4 py-3.5 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-600 focus:outline-none focus:border-violet-500/50"
                data-testid="account-number-input"
              />
            </div>

            {/* Account Name */}
            <div>
              <label className="text-sm text-gray-400 mb-2 block">Account Name</label>
              <input
                type="text"
                value={accountName}
                onChange={(e) => setAccountName(e.target.value)}
                placeholder="Juan Dela Cruz"
                className="w-full px-4 py-3.5 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-600 focus:outline-none focus:border-violet-500/50"
                data-testid="account-name-input"
              />
            </div>

            {/* Error Display */}
            {error && (
              <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl flex items-center gap-3">
                <AlertCircle className="w-5 h-5 text-red-400 shrink-0" />
                <p className="text-red-400 text-sm">{error}</p>
              </div>
            )}

            <div className="flex gap-3">
              <button
                onClick={() => setStep(1)}
                className="flex-1 py-4 bg-white/5 hover:bg-white/10 text-white font-semibold rounded-xl transition-all"
              >
                Back
              </button>
              <button
                onClick={handleSubmit}
                disabled={!accountNumber || !accountName || submitting}
                className="flex-1 py-4 bg-red-600 hover:bg-red-500 disabled:bg-gray-700 disabled:text-gray-500 text-white font-semibold rounded-xl transition-all flex items-center justify-center gap-2"
                data-testid="submit-btn"
              >
                {submitting ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Processing...
                  </>
                ) : (
                  'Confirm Withdrawal'
                )}
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default Withdraw;

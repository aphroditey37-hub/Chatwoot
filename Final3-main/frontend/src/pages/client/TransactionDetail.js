/**
 * TransactionDetail - Migrated to new API layer
 * Route: /client/wallet/transaction/:orderId
 * 
 * Features:
 * - Header with order ID, status badge, amount
 * - Vertical timeline
 * - Failure/rejection card if present
 * - Void record card if present
 * - Loading, error, retry states
 */

import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { 
  ArrowLeft, Clock, Check, X, AlertCircle, RefreshCw,
  Plus, Upload, Edit, Zap, Activity, DollarSign,
  Ban, Info, ArrowDownLeft, ArrowUpRight, Loader2
} from 'lucide-react';

// Centralized API
import http, { getErrorMessage, isServerUnavailable } from '../../api/http';
import { PageLoader } from '../../features/shared/LoadingStates';

const TransactionDetail = () => {
  const navigate = useNavigate();
  const { orderId } = useParams();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isNetworkError, setIsNetworkError] = useState(false);
  const [data, setData] = useState(null);

  const fetchTransactionDetail = useCallback(async () => {
    setLoading(true);
    setError(null);
    setIsNetworkError(false);
    
    try {
      const response = await http.get(`/portal/transactions/${orderId}`);
      setData(response.data);
    } catch (err) {
      const message = getErrorMessage(err, 'Failed to load transaction details');
      setError(message);
      setIsNetworkError(isServerUnavailable(err));
    } finally {
      setLoading(false);
    }
  }, [orderId]);

  useEffect(() => {
    fetchTransactionDetail();
  }, [fetchTransactionDetail]);

  const getStatusColor = (status) => {
    switch (status) {
      case 'approved':
      case 'completed':
        return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
      case 'pending':
      case 'pending_approval':
      case 'pending_review':
      case 'initiated':
      case 'awaiting_payment_proof':
        return 'bg-amber-500/20 text-amber-400 border-amber-500/30';
      case 'failed':
      case 'rejected':
      case 'cancelled':
        return 'bg-red-500/20 text-red-400 border-red-500/30';
      default:
        return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
    }
  };

  const getTimelineIcon = (icon, event) => {
    const iconClass = "w-4 h-4";
    switch (icon) {
      case 'plus':
        return <Plus className={iconClass} />;
      case 'upload':
        return <Upload className={iconClass} />;
      case 'edit':
        return <Edit className={iconClass} />;
      case 'check':
        return <Check className={iconClass} />;
      case 'x':
        return <X className={iconClass} />;
      case 'zap':
        return <Zap className={iconClass} />;
      default:
        return <Activity className={iconClass} />;
    }
  };

  const getTimelineColor = (event) => {
    if (!event) return 'bg-gray-600 text-white';
    if (event.includes('approved') || event.includes('completed') || event.includes('executed')) {
      return 'bg-emerald-500 text-white';
    }
    if (event.includes('rejected') || event.includes('cancelled')) {
      return 'bg-red-500 text-white';
    }
    if (event.includes('created') || event.includes('uploaded')) {
      return 'bg-violet-500 text-white';
    }
    if (event.includes('adjusted')) {
      return 'bg-amber-500 text-white';
    }
    return 'bg-gray-600 text-white';
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
    return <PageLoader message="Loading transaction..." />;
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#0a0a0f] flex flex-col items-center justify-center p-4">
        <div className="w-16 h-16 bg-red-500/10 rounded-full flex items-center justify-center mb-4">
          {isNetworkError ? (
            <RefreshCw className="w-8 h-8 text-amber-400" />
          ) : (
            <AlertCircle className="w-8 h-8 text-red-400" />
          )}
        </div>
        <p className={`text-center mb-6 ${isNetworkError ? 'text-amber-400' : 'text-red-400'}`}>
          {error}
        </p>
        <div className="flex gap-3">
          <button
            onClick={fetchTransactionDetail}
            className="flex items-center gap-2 px-4 py-2 bg-violet-600 hover:bg-violet-500 text-white rounded-lg transition-colors"
            data-testid="retry-btn"
          >
            <RefreshCw className="w-4 h-4" />
            Retry
          </button>
          <button
            onClick={() => navigate('/client/wallet')}
            className="flex items-center gap-2 px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Wallet
          </button>
        </div>
      </div>
    );
  }

  const { order, timeline, summary } = data || {};
  const isDeposit = order?.order_type?.includes('load') || order?.order_type?.includes('deposit');

  return (
    <div className="min-h-screen bg-[#0a0a0f] pb-8" data-testid="transaction-detail">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-[#0a0a0f]/90 backdrop-blur-xl border-b border-white/5">
        <div className="px-4 py-4 flex items-center gap-4">
          <button
            onClick={() => navigate('/client/wallet')}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors"
            data-testid="back-btn"
          >
            <ArrowLeft className="w-5 h-5 text-white" />
          </button>
          <div>
            <h1 className="text-lg font-bold text-white">Transaction Details</h1>
            <p className="text-xs text-gray-500 font-mono">#{order?.order_id?.slice(0, 8) || orderId.slice(0, 8)}...</p>
          </div>
        </div>
      </header>

      <main className="px-4 py-6 space-y-6 max-w-2xl mx-auto">
        {/* Status Card */}
        <div className="relative overflow-hidden p-6 bg-gradient-to-br from-gray-900 via-gray-900 to-gray-800 border border-white/10 rounded-2xl">
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                isDeposit ? 'bg-emerald-500/20' : 'bg-red-500/20'
              }`}>
                {isDeposit ? (
                  <ArrowDownLeft className="w-6 h-6 text-emerald-400" />
                ) : (
                  <ArrowUpRight className="w-6 h-6 text-red-400" />
                )}
              </div>
              <div>
                <p className="font-semibold text-white">
                  {order?.order_type?.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) || 'Transaction'}
                </p>
                {order?.game && (
                  <p className="text-sm text-gray-400">{order.game}</p>
                )}
              </div>
            </div>
            <span className={`px-3 py-1.5 rounded-full text-sm font-medium border ${getStatusColor(order?.status)}`}>
              {order?.status_label || order?.status || 'Unknown'}
            </span>
          </div>

          {/* Amount */}
          <div className="text-center py-4 border-y border-white/10">
            <p className="text-sm text-gray-400 mb-1">Amount</p>
            <p className={`text-3xl font-bold ${isDeposit ? 'text-emerald-400' : 'text-red-400'}`}>
              {isDeposit ? '+' : '-'}${order?.amount?.toFixed(2) || '0.00'}
            </p>
            {order?.bonus_amount > 0 && (
              <p className="text-sm text-violet-400 mt-1">
                +${order.bonus_amount.toFixed(2)} bonus
              </p>
            )}
          </div>

          {/* Quick Stats */}
          <div className="grid grid-cols-2 gap-4 mt-4">
            <div>
              <p className="text-xs text-gray-500">Created</p>
              <p className="text-sm text-white">{formatDate(order?.created_at)}</p>
            </div>
            {order?.approved_at && (
              <div>
                <p className="text-xs text-gray-500">Processed</p>
                <p className="text-sm text-white">{formatDate(order.approved_at)}</p>
              </div>
            )}
          </div>
        </div>

        {/* Void Warning */}
        {order?.void_amount > 0 && (
          <div className="flex items-start gap-3 p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl">
            <Info className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <p className="text-amber-400 font-medium">Amount Voided: ${order.void_amount.toFixed(2)}</p>
              {order.void_reason && (
                <p className="text-amber-400/80 text-sm mt-1">{String(order.void_reason)}</p>
              )}
            </div>
          </div>
        )}

        {/* Rejection Reason */}
        {order?.rejection_reason && (
          <div className="flex items-start gap-3 p-4 bg-red-500/10 border border-red-500/30 rounded-xl">
            <Ban className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
            <div>
              <p className="text-red-400 font-medium">Rejection Reason</p>
              <p className="text-red-400/80 text-sm mt-1">{String(order.rejection_reason)}</p>
            </div>
          </div>
        )}

        {/* Payout Info */}
        {order?.payout_amount > 0 && (
          <div className="flex items-start gap-3 p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-xl">
            <DollarSign className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
            <div>
              <p className="text-emerald-400 font-medium">Payout Amount</p>
              <p className="text-emerald-400 text-2xl font-bold mt-1">${order.payout_amount.toFixed(2)}</p>
            </div>
          </div>
        )}

        {/* Timeline */}
        <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-6">
          <h3 className="font-semibold text-white mb-6 flex items-center gap-2">
            <Clock className="w-5 h-5 text-violet-400" />
            Activity Timeline
          </h3>

          {timeline && timeline.length > 0 ? (
            <div className="relative">
              {/* Timeline line */}
              <div className="absolute left-[18px] top-2 bottom-2 w-0.5 bg-gradient-to-b from-violet-500/50 via-gray-700 to-gray-800" />

              <div className="space-y-6">
                {timeline.map((event, index) => (
                  <div key={index} className="relative flex gap-4">
                    {/* Icon */}
                    <div className={`relative z-10 w-9 h-9 rounded-full flex items-center justify-center shrink-0 ${getTimelineColor(event.event)}`}>
                      {getTimelineIcon(event.icon, event.event)}
                    </div>

                    {/* Content */}
                    <div className="flex-1 pb-2">
                      <div className="flex items-start justify-between gap-2">
                        <p className="font-medium text-white">{event.title || 'Event'}</p>
                        <p className="text-xs text-gray-500 whitespace-nowrap">
                          {formatDate(event.timestamp)}
                        </p>
                      </div>
                      <p className="text-sm text-gray-400 mt-1">{event.description || ''}</p>
                      {event.actor && event.actor !== 'System' && (
                        <p className="text-xs text-gray-600 mt-1">by {event.actor}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="text-center py-8">
              <Activity className="w-10 h-10 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-500">No activity recorded</p>
            </div>
          )}
        </div>

        {/* Summary */}
        {summary && (
          <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-4">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-500">Status</span>
              <span className={summary.is_final ? 'text-emerald-400' : 'text-amber-400'}>
                {summary.is_final ? 'Final' : 'In Progress'}
              </span>
            </div>
            <div className="flex items-center justify-between text-sm mt-2">
              <span className="text-gray-500">Timeline Events</span>
              <span className="text-white">{summary.total_events || 0}</span>
            </div>
          </div>
        )}

        {/* Adjusted Badge */}
        {order?.amount_was_adjusted && (
          <div className="text-center">
            <span className="inline-flex items-center gap-1 px-3 py-1 bg-amber-500/10 text-amber-400 text-xs rounded-full border border-amber-500/30">
              <Edit className="w-3 h-3" />
              Amount was adjusted by admin
            </span>
          </div>
        )}
      </main>
    </div>
  );
};

export default TransactionDetail;

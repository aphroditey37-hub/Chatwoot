/**
 * Admin Balance Control Page
 * Manually load/withdraw client balances with Telegram approval
 * Uses centralized admin API client
 */
import React, { useEffect, useState, useCallback } from 'react';
import { toast } from 'sonner';
import { 
  Search, Plus, Minus, RefreshCw, User, DollarSign, 
  AlertCircle, Clock, Send, AlertTriangle, X
} from 'lucide-react';

// Centralized Admin API
import { balanceControlApi, usersApi, ordersApi, getErrorMessage } from '../../api/admin';

// Confirmation Modal Component
const ConfirmationModal = ({ isOpen, onClose, onConfirm, actionType, clientName, amount, reason, isSubmitting }) => {
  if (!isOpen) return null;
  
  const isLoad = actionType === 'load';
  
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="relative bg-gray-900 border border-gray-700 rounded-2xl p-6 w-full max-w-md shadow-2xl">
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1 text-gray-400 hover:text-white rounded-lg hover:bg-gray-800"
        >
          <X className="w-5 h-5" />
        </button>
        
        {/* Icon */}
        <div className={`w-16 h-16 mx-auto mb-4 rounded-full flex items-center justify-center ${
          isLoad ? 'bg-emerald-500/20' : 'bg-red-500/20'
        }`}>
          <AlertTriangle className={`w-8 h-8 ${isLoad ? 'text-emerald-400' : 'text-red-400'}`} />
        </div>
        
        {/* Title */}
        <h3 className="text-xl font-bold text-white text-center mb-2">
          Confirm {isLoad ? 'Balance Load' : 'Balance Withdrawal'}
        </h3>
        
        {/* Description */}
        <p className="text-gray-400 text-center mb-6">
          This action will be executed immediately. Please review the details below.
        </p>
        
        {/* Details Card */}
        <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4 space-y-3 mb-6">
          <div className="flex justify-between">
            <span className="text-gray-400">Client</span>
            <span className="text-white font-medium">{clientName}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Action</span>
            <span className={`font-medium ${isLoad ? 'text-emerald-400' : 'text-red-400'}`}>
              {isLoad ? 'Load Balance' : 'Withdraw Balance'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Amount</span>
            <span className={`font-bold text-lg ${isLoad ? 'text-emerald-400' : 'text-red-400'}`}>
              {isLoad ? '+' : '-'}${parseFloat(amount).toFixed(2)}
            </span>
          </div>
          <div className="pt-2 border-t border-gray-700">
            <span className="text-gray-400 text-sm">Reason:</span>
            <p className="text-white text-sm mt-1">{reason}</p>
          </div>
        </div>
        
        {/* Info Notice */}
        <div className="flex items-start gap-2 p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg mb-6">
          <AlertCircle className="w-5 h-5 text-blue-400 shrink-0 mt-0.5" />
          <p className="text-blue-400 text-sm">
            This action will be logged in the audit trail for compliance.
          </p>
        </div>
        
        {/* Buttons */}
        <div className="flex gap-3">
          <button
            onClick={onClose}
            disabled={isSubmitting}
            className="flex-1 py-3 px-4 bg-gray-800 hover:bg-gray-700 text-white font-medium rounded-xl transition-colors disabled:opacity-50"
            data-testid="confirm-cancel-btn"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={isSubmitting}
            className={`flex-1 py-3 px-4 font-semibold rounded-xl transition-colors flex items-center justify-center gap-2 ${
              isLoad 
                ? 'bg-emerald-600 hover:bg-emerald-500 text-white' 
                : 'bg-red-600 hover:bg-red-500 text-white'
            } disabled:opacity-50`}
            data-testid="confirm-submit-btn"
          >
            {isSubmitting ? (
              <RefreshCw className="w-5 h-5 animate-spin" />
            ) : (
              <>
                <Send className="w-4 h-4" />
                Confirm
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

const AdminBalanceControl = () => {
  const [loading, setLoading] = useState(true);
  const [clients, setClients] = useState([]);
  const [search, setSearch] = useState('');
  const [selectedClient, setSelectedClient] = useState(null);
  const [actionType, setActionType] = useState('load'); // 'load' or 'withdraw'
  const [amount, setAmount] = useState('');
  const [reason, setReason] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [recentActions, setRecentActions] = useState([]);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [error, setError] = useState(null);

  const fetchClients = useCallback(async () => {
    try {
      const response = await usersApi.getAll({ limit: 500 });
      const clientsData = Array.isArray(response.data) ? response.data : (response.data.clients || []);
      setClients(clientsData);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch clients:', err);
      setError(getErrorMessage(err, 'Failed to load clients'));
      toast.error('Failed to load clients');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchRecentActions = useCallback(async () => {
    try {
      // Backend expects single order_type, so fetch both and combine
      const [loadRes, withdrawRes] = await Promise.all([
        ordersApi.getAll({ order_type: 'admin_load', limit: 10 }),
        ordersApi.getAll({ order_type: 'admin_withdraw', limit: 10 })
      ]);
      const combined = [
        ...(loadRes.data.orders || []),
        ...(withdrawRes.data.orders || [])
      ].sort((a, b) => new Date(b.created_at) - new Date(a.created_at)).slice(0, 20);
      setRecentActions(combined);
    } catch (err) {
      console.error('Failed to fetch recent actions:', err);
    }
  }, []);

  useEffect(() => {
    fetchClients();
    fetchRecentActions();
  }, [fetchClients, fetchRecentActions]);

  const handleSubmit = async () => {
    if (!selectedClient) {
      toast.error('Please select a client');
      return;
    }
    if (!amount || parseFloat(amount) <= 0) {
      toast.error('Please enter a valid amount');
      return;
    }
    if (!reason || reason.length < 5) {
      toast.error('Please provide a reason (min 5 characters)');
      return;
    }

    // Show confirmation modal instead of submitting directly
    setShowConfirmModal(true);
  };

  const handleConfirmedSubmit = async () => {
    setSubmitting(true);
    try {
      const amountValue = parseFloat(amount);
      
      let response;
      if (actionType === 'load') {
        response = await balanceControlApi.load(selectedClient.user_id, amountValue, reason);
      } else {
        response = await balanceControlApi.withdraw(selectedClient.user_id, amountValue, reason);
      }

      if (response.data.success) {
        toast.success(response.data.message || `${actionType === 'load' ? 'Load' : 'Withdraw'} request submitted`);
        setAmount('');
        setReason('');
        setSelectedClient(null);
        setShowConfirmModal(false);
        fetchClients();
        fetchRecentActions();
      }
    } catch (err) {
      toast.error(getErrorMessage(err, 'Operation failed'));
    } finally {
      setSubmitting(false);
    }
  };

  const filteredClients = clients.filter(c => 
    c.username?.toLowerCase().includes(search.toLowerCase()) ||
    c.display_name?.toLowerCase().includes(search.toLowerCase()) ||
    c.email?.toLowerCase().includes(search.toLowerCase())
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-violet-500" />
      </div>
    );
  }

  if (error && clients.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-3" />
          <p className="text-red-400 mb-4">{error}</p>
          <button 
            onClick={fetchClients} 
            className="px-4 py-2 bg-violet-600 hover:bg-violet-500 rounded-lg text-white"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="admin-balance-control">
      {/* Confirmation Modal */}
      <ConfirmationModal
        isOpen={showConfirmModal}
        onClose={() => setShowConfirmModal(false)}
        onConfirm={handleConfirmedSubmit}
        actionType={actionType}
        clientName={selectedClient?.display_name || selectedClient?.username || ''}
        amount={amount}
        reason={reason}
        isSubmitting={submitting}
      />

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <DollarSign className="w-6 h-6 text-emerald-400" />
            Client Balance Control
          </h1>
          <p className="text-gray-400 text-sm">Manually adjust client balances (instant execution)</p>
        </div>
        <button 
          onClick={() => { fetchClients(); fetchRecentActions(); }}
          className="p-2 hover:bg-gray-800 rounded-lg text-gray-400 hover:text-white"
          data-testid="refresh-btn"
        >
          <RefreshCw className="w-5 h-5" />
        </button>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Balance Adjustment Form */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Adjust Balance</h2>
          
          {/* Action Type Toggle */}
          <div className="flex gap-2 mb-6">
            <button
              onClick={() => setActionType('load')}
              className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-xl font-medium transition-all ${
                actionType === 'load'
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/50'
                  : 'bg-gray-800 text-gray-400 border border-gray-700 hover:border-gray-600'
              }`}
              data-testid="action-load"
            >
              <Plus className="w-5 h-5" />
              Load Balance
            </button>
            <button
              onClick={() => setActionType('withdraw')}
              className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-xl font-medium transition-all ${
                actionType === 'withdraw'
                  ? 'bg-red-500/20 text-red-400 border border-red-500/50'
                  : 'bg-gray-800 text-gray-400 border border-gray-700 hover:border-gray-600'
              }`}
              data-testid="action-withdraw"
            >
              <Minus className="w-5 h-5" />
              Withdraw Balance
            </button>
          </div>

          {/* Client Search */}
          <div className="mb-4">
            <label className="text-sm text-gray-400 mb-2 block">Select Client</label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by username or email..."
                className="w-full pl-10 pr-4 py-3 bg-gray-800 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-violet-500"
                data-testid="client-search"
              />
            </div>
            
            {/* Client List */}
            {search && (
              <div className="mt-2 max-h-48 overflow-y-auto bg-gray-800 border border-gray-700 rounded-xl">
                {filteredClients.length === 0 ? (
                  <p className="text-gray-500 text-sm p-3 text-center">No clients found</p>
                ) : (
                  filteredClients.slice(0, 10).map(client => (
                    <button
                      key={client.user_id}
                      onClick={() => { setSelectedClient(client); setSearch(''); }}
                      className="w-full flex items-center gap-3 p-3 hover:bg-gray-700 transition-colors text-left"
                      data-testid={`client-${client.user_id}`}
                    >
                      <div className="w-8 h-8 rounded-full bg-violet-500/20 flex items-center justify-center">
                        <User className="w-4 h-4 text-violet-400" />
                      </div>
                      <div>
                        <p className="text-white text-sm font-medium">{client.display_name || client.username}</p>
                        <p className="text-gray-500 text-xs">@{client.username} • ${(client.balance?.real ?? client.real_balance ?? 0).toFixed(2)}</p>
                      </div>
                    </button>
                  ))
                )}
              </div>
            )}
          </div>

          {/* Selected Client Display */}
          {selectedClient && (
            <div className="mb-4 p-4 bg-violet-500/10 border border-violet-500/30 rounded-xl">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-violet-500/20 flex items-center justify-center">
                    <User className="w-5 h-5 text-violet-400" />
                  </div>
                  <div>
                    <p className="text-white font-medium">{selectedClient.display_name || selectedClient.username}</p>
                    <p className="text-violet-400 text-sm">Balance: ${(selectedClient.balance?.real ?? selectedClient.real_balance ?? 0).toFixed(2)}</p>
                  </div>
                </div>
                <button
                  onClick={() => setSelectedClient(null)}
                  className="text-gray-400 hover:text-white p-1"
                  data-testid="clear-client"
                >
                  ×
                </button>
              </div>
            </div>
          )}

          {/* Amount Input */}
          <div className="mb-4">
            <label className="text-sm text-gray-400 mb-2 block">Amount ($)</label>
            <div className="relative">
              <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
              <input
                type="number"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="0.00"
                min="0"
                step="0.01"
                className="w-full pl-10 pr-4 py-3 bg-gray-800 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-violet-500"
                data-testid="amount-input"
              />
            </div>
          </div>

          {/* Reason Input */}
          <div className="mb-6">
            <label className="text-sm text-gray-400 mb-2 block">Reason (Required)</label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Explain why this adjustment is needed..."
              rows={3}
              className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-violet-500 resize-none"
              data-testid="reason-input"
            />
          </div>

          {/* Info Notice */}
          <div className="mb-6 p-4 bg-blue-500/10 border border-blue-500/30 rounded-xl flex gap-3">
            <AlertCircle className="w-5 h-5 text-blue-400 shrink-0 mt-0.5" />
            <div className="text-sm">
              <p className="text-blue-400 font-medium">Instant Execution</p>
              <p className="text-blue-400/80">Balance changes are applied immediately and logged for audit.</p>
            </div>
          </div>

          {/* Submit Button */}
          <button
            onClick={handleSubmit}
            disabled={!selectedClient || !amount || !reason || submitting}
            className={`w-full flex items-center justify-center gap-2 py-4 rounded-xl font-semibold transition-all ${
              actionType === 'load'
                ? 'bg-emerald-600 hover:bg-emerald-500 disabled:bg-gray-700'
                : 'bg-red-600 hover:bg-red-500 disabled:bg-gray-700'
            } text-white disabled:text-gray-500`}
            data-testid="submit-btn"
          >
            {submitting ? (
              <RefreshCw className="w-5 h-5 animate-spin" />
            ) : (
              <>
                <Send className="w-5 h-5" />
                {actionType === 'load' ? 'Load Balance Now' : 'Withdraw Balance Now'}
              </>
            )}
          </button>
        </div>

        {/* Right: Recent Actions */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Recent Admin Actions</h2>
          
          {recentActions.length === 0 ? (
            <div className="text-center py-12">
              <Clock className="w-12 h-12 text-gray-700 mx-auto mb-3" />
              <p className="text-gray-500">No recent admin actions</p>
            </div>
          ) : (
            <div className="space-y-3 max-h-[500px] overflow-y-auto">
              {recentActions.map(action => (
                <div
                  key={action.order_id}
                  className="p-4 bg-gray-800/50 border border-gray-700/50 rounded-xl"
                  data-testid={`action-${action.order_id}`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                        action.order_type?.includes('load') 
                          ? 'bg-emerald-500/20' 
                          : 'bg-red-500/20'
                      }`}>
                        {action.order_type?.includes('load') ? (
                          <Plus className="w-4 h-4 text-emerald-400" />
                        ) : (
                          <Minus className="w-4 h-4 text-red-400" />
                        )}
                      </div>
                      <div>
                        <p className="text-white text-sm font-medium">
                          {action.order_type?.includes('load') ? 'Manual Load' : 'Manual Withdraw'}
                        </p>
                        <p className="text-gray-500 text-xs">@{action.username}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className={`font-semibold ${
                        action.order_type?.includes('load') ? 'text-emerald-400' : 'text-red-400'
                      }`}>
                        {action.order_type?.includes('load') ? '+' : '-'}${action.amount?.toFixed(2)}
                      </p>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        action.status === 'approved' || action.status === 'completed' || action.status === 'APPROVED_EXECUTED'
                          ? 'bg-emerald-500/20 text-emerald-400'
                          : action.status === 'pending' || action.status === 'pending_approval'
                          ? 'bg-amber-500/20 text-amber-400'
                          : 'bg-red-500/20 text-red-400'
                      }`}>
                        {action.status === 'APPROVED_EXECUTED' ? 'Executed' : action.status?.replace(/_/g, ' ')}
                      </span>
                    </div>
                  </div>
                  {action.metadata?.reason && (
                    <p className="text-gray-400 text-xs mt-2 line-clamp-2">
                      Reason: {action.metadata.reason}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AdminBalanceControl;

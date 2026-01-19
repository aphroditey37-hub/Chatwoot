import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { 
  ArrowLeft, User, Ban, CheckCircle, Lock, Unlock, Key, DollarSign, 
  TrendingUp, TrendingDown, Plus, Eye, EyeOff, Shield, Save, 
  AlertTriangle, Settings, Clock, ArrowDown, ArrowUp, Gift, XCircle,
  BarChart3, RefreshCw, AlertCircle
} from 'lucide-react';

// Centralized Admin API
import { usersApi, gamesApi, analyticsApi, getErrorMessage } from '../../api/admin';

const AdminClientDetail = () => {
  const { clientId } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [clientData, setClientData] = useState(null);
  const [showCredModal, setShowCredModal] = useState(false);
  const [credForm, setCredForm] = useState({ game_id: '', game_user_id: '', game_password: '' });
  const [games, setGames] = useState([]);
  const [overrides, setOverrides] = useState({
    custom_deposit_bonus: null,
    custom_cashout_min: null,
    custom_cashout_max: null,
    manual_approval_required: false,
    bonus_disabled: false,
    withdraw_disabled: false
  });
  const [activityTimeline, setActivityTimeline] = useState([]);
  const [clientAnalytics, setClientAnalytics] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');

  const fetchClientDetail = useCallback(async () => {
    try {
      const response = await usersApi.getById(clientId);
      setClientData(response.data);
    } catch (err) {
      console.error('Failed to fetch client:', err);
      setError(getErrorMessage(err, 'Failed to load client details'));
    } finally {
      setLoading(false);
    }
  }, [clientId]);

  const fetchClientAnalytics = useCallback(async () => {
    try {
      const response = await analyticsApi.getClientAnalytics(clientId);
      setClientAnalytics(response.data);
    } catch (err) {
      console.error('Failed to fetch client analytics:', err);
    }
  }, [clientId]);

  const fetchGames = useCallback(async () => {
    try {
      const response = await gamesApi.getAll();
      const gamesData = Array.isArray(response.data) ? response.data : (response.data.games || []);
      setGames(gamesData);
    } catch (err) {
      console.error('Failed to fetch games:', err);
      setGames([]);
    }
  }, []);

  const fetchClientOverrides = useCallback(async () => {
    try {
      const response = await usersApi.getOverrides(clientId);
      if (response.data) {
        setOverrides({
          custom_deposit_bonus: response.data.custom_deposit_bonus,
          custom_cashout_min: response.data.custom_cashout_min,
          custom_cashout_max: response.data.custom_cashout_max,
          manual_approval_required: response.data.manual_approval_required || false,
          bonus_disabled: response.data.bonus_disabled || false,
          withdraw_disabled: response.data.withdraw_disabled || false
        });
      }
    } catch (err) {
      console.error('Failed to fetch overrides:', err);
    }
  }, [clientId]);

  const fetchActivityTimeline = useCallback(async () => {
    try {
      const response = await usersApi.getActivity(clientId);
      setActivityTimeline(response.data.activities || []);
    } catch (err) {
      console.error('Failed to fetch activity:', err);
    }
  }, [clientId]);

  useEffect(() => {
    fetchClientDetail();
    fetchGames();
    fetchClientOverrides();
    fetchActivityTimeline();
    fetchClientAnalytics();
  }, [fetchClientDetail, fetchGames, fetchClientOverrides, fetchActivityTimeline, fetchClientAnalytics]);

  const handleSaveOverrides = async () => {
    try {
      await usersApi.updateOverrides(clientId, overrides);
      toast.success('Client overrides saved successfully');
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to save overrides'));
    }
  };

  const handleStatusUpdate = async (newStatus) => {
    try {
      await usersApi.update(clientId, { status: newStatus });
      toast.success(`Client status updated to ${newStatus}`);
      fetchClientDetail();
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to update status'));
    }
  };

  const handleLockToggle = async (field, value) => {
    try {
      await usersApi.update(clientId, { [field]: value });
      toast.success('Setting updated');
      fetchClientDetail();
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to update'));
    }
  };

  const handleVisibilityChange = async (newLevel) => {
    try {
      await usersApi.update(clientId, { visibility_level: newLevel });
      toast.success('Visibility updated');
      fetchClientDetail();
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to update visibility'));
    }
  };

  const handleAssignCredential = async () => {
    if (!credForm.game_id || !credForm.game_user_id || !credForm.game_password) {
      toast.error('Please fill all fields');
      return;
    }
    try {
      await usersApi.assignCredential(clientId, {
        client_id: clientId,
        ...credForm
      });
      setShowCredModal(false);
      setCredForm({ game_id: '', game_user_id: '', game_password: '' });
      toast.success('Credentials assigned successfully');
      fetchClientDetail();
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to assign credentials'));
    }
  };

  // Loading State
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-emerald-500" />
      </div>
    );
  }

  // Error State
  if (error && !clientData) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-3" />
          <p className="text-red-400 mb-4">{error}</p>
          <button 
            onClick={() => navigate('/admin/clients')}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition"
          >
            Back to Clients
          </button>
        </div>
      </div>
    );
  }

  if (!clientData) {
    return <div className="text-white text-center py-8">Client not found</div>;
  }

  const { client, financial_summary, credentials, recent_transactions, recent_orders } = clientData;

  // Analytics Tab Component
  const AnalyticsTab = () => (
    <div className="space-y-6">
      {/* Current Balances */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
          <DollarSign className="w-5 h-5 text-emerald-400" />
          Current Balances
        </h3>
        <div className="grid grid-cols-4 gap-4">
          <div className="p-3 bg-gray-800 rounded-lg">
            <p className="text-gray-400 text-xs">Cash</p>
            <p className="text-xl font-bold text-emerald-400">${clientAnalytics?.balances?.cash?.toLocaleString() || '0'}</p>
          </div>
          <div className="p-3 bg-gray-800 rounded-lg">
            <p className="text-gray-400 text-xs">Bonus</p>
            <p className="text-xl font-bold text-purple-400">${clientAnalytics?.balances?.bonus?.toLocaleString() || '0'}</p>
          </div>
          <div className="p-3 bg-gray-800 rounded-lg">
            <p className="text-gray-400 text-xs">Play Credits</p>
            <p className="text-xl font-bold text-blue-400">${clientAnalytics?.balances?.play_credits?.toLocaleString() || '0'}</p>
          </div>
          <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg">
            <p className="text-emerald-400 text-xs">Total</p>
            <p className="text-xl font-bold text-emerald-400">${clientAnalytics?.balances?.total?.toLocaleString() || '0'}</p>
          </div>
        </div>
      </div>

      {/* Withdrawal Status */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
          <Lock className="w-5 h-5 text-yellow-400" />
          Withdrawal Status
        </h3>
        <div className="grid grid-cols-3 gap-4">
          <div className={`p-3 rounded-lg ${clientAnalytics?.withdrawal_status?.locked ? 'bg-red-500/10 border border-red-500/30' : 'bg-emerald-500/10 border border-emerald-500/30'}`}>
            <p className={`text-xs ${clientAnalytics?.withdrawal_status?.locked ? 'text-red-400' : 'text-emerald-400'}`}>Status</p>
            <p className={`text-lg font-bold ${clientAnalytics?.withdrawal_status?.locked ? 'text-red-400' : 'text-emerald-400'}`}>
              {clientAnalytics?.withdrawal_status?.locked ? 'LOCKED' : 'UNLOCKED'}
            </p>
          </div>
          <div className="p-3 bg-gray-800 rounded-lg">
            <p className="text-gray-400 text-xs">Withdrawable</p>
            <p className="text-xl font-bold text-white">${clientAnalytics?.withdrawal_status?.withdrawable?.toLocaleString() || '0'}</p>
          </div>
          <div className="p-3 bg-gray-800 rounded-lg">
            <p className="text-gray-400 text-xs">Locked Amount</p>
            <p className="text-xl font-bold text-yellow-400">${clientAnalytics?.withdrawal_status?.locked_amount?.toLocaleString() || '0'}</p>
          </div>
        </div>
      </div>

      {/* Cashout Projection */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-purple-400" />
          Cashout Projection
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-3 bg-purple-500/10 border border-purple-500/30 rounded-lg">
            <p className="text-purple-400 text-xs">Max Eligible Cashout</p>
            <p className="text-xl font-bold text-purple-400">${clientAnalytics?.cashout_projection?.max_eligible_cashout?.toLocaleString() || '0'}</p>
          </div>
          <div className="p-3 bg-orange-500/10 border border-orange-500/30 rounded-lg">
            <p className="text-orange-400 text-xs">Expected Void</p>
            <p className="text-xl font-bold text-orange-400">${clientAnalytics?.cashout_projection?.expected_void_if_withdrawn?.toLocaleString() || '0'}</p>
          </div>
          <div className="p-3 bg-gray-800 rounded-lg">
            <p className="text-gray-400 text-xs">Max Multiplier</p>
            <p className="text-xl font-bold text-white">{clientAnalytics?.cashout_projection?.max_multiplier || 3}x</p>
          </div>
          <div className="p-3 bg-gray-800 rounded-lg">
            <p className="text-gray-400 text-xs">Total Deposited</p>
            <p className="text-xl font-bold text-white">${clientAnalytics?.cashout_projection?.total_deposited?.toLocaleString() || '0'}</p>
          </div>
        </div>
      </div>

      {/* Lifetime Stats */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-blue-400" />
          Lifetime Statistics
        </h3>
        <div className="grid grid-cols-3 md:grid-cols-6 gap-4">
          <div className="p-3 bg-gray-800 rounded-lg">
            <p className="text-gray-400 text-xs">Deposits</p>
            <p className="text-lg font-bold text-emerald-400">${clientAnalytics?.lifetime_stats?.deposits?.toLocaleString() || '0'}</p>
            <p className="text-gray-500 text-xs">{clientAnalytics?.lifetime_stats?.deposit_count || 0} txns</p>
          </div>
          <div className="p-3 bg-gray-800 rounded-lg">
            <p className="text-gray-400 text-xs">Withdrawals</p>
            <p className="text-lg font-bold text-red-400">${clientAnalytics?.lifetime_stats?.withdrawals?.toLocaleString() || '0'}</p>
            <p className="text-gray-500 text-xs">{clientAnalytics?.lifetime_stats?.withdrawal_count || 0} txns</p>
          </div>
          <div className="p-3 bg-gray-800 rounded-lg">
            <p className="text-gray-400 text-xs">Bonus Received</p>
            <p className="text-lg font-bold text-purple-400">${clientAnalytics?.lifetime_stats?.bonus_received?.toLocaleString() || '0'}</p>
          </div>
          <div className="p-3 bg-gray-800 rounded-lg">
            <p className="text-gray-400 text-xs">Voided</p>
            <p className="text-lg font-bold text-orange-400">${clientAnalytics?.lifetime_stats?.voided?.toLocaleString() || '0'}</p>
          </div>
          <div className="p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg col-span-2">
            <p className="text-blue-400 text-xs">Net (Deposits - Withdrawals)</p>
            <p className={`text-lg font-bold ${(clientAnalytics?.lifetime_stats?.deposits || 0) - (clientAnalytics?.lifetime_stats?.withdrawals || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
              ${((clientAnalytics?.lifetime_stats?.deposits || 0) - (clientAnalytics?.lifetime_stats?.withdrawals || 0)).toLocaleString()}
            </p>
          </div>
        </div>
      </div>

      {/* Risk Flags */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-orange-400" />
          Risk Flags
        </h3>
        <div className="flex gap-3">
          <div className={`px-4 py-2 rounded-lg ${clientAnalytics?.risk_flags?.is_suspicious ? 'bg-red-500/20 border border-red-500/50' : 'bg-gray-800'}`}>
            <span className={clientAnalytics?.risk_flags?.is_suspicious ? 'text-red-400' : 'text-gray-400'}>
              {clientAnalytics?.risk_flags?.is_suspicious ? '⚠️ Suspicious' : '✓ Not Suspicious'}
            </span>
          </div>
          <div className={`px-4 py-2 rounded-lg ${clientAnalytics?.risk_flags?.withdraw_locked ? 'bg-yellow-500/20 border border-yellow-500/50' : 'bg-gray-800'}`}>
            <span className={clientAnalytics?.risk_flags?.withdraw_locked ? 'text-yellow-400' : 'text-gray-400'}>
              {clientAnalytics?.risk_flags?.withdraw_locked ? '🔒 Withdraw Locked' : '✓ Withdraw Unlocked'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate('/admin/clients')}
          className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
        >
          <ArrowLeft className="w-6 h-6 text-gray-400" />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-white">{client.display_name}</h1>
          <p className="text-gray-400 text-sm">{client.client_id}</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-gray-800 pb-2">
        <button
          onClick={() => setActiveTab('overview')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition ${activeTab === 'overview' ? 'bg-emerald-500/20 text-emerald-400' : 'text-gray-400 hover:text-white'}`}
        >
          Overview
        </button>
        <button
          onClick={() => setActiveTab('analytics')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition flex items-center gap-2 ${activeTab === 'analytics' ? 'bg-blue-500/20 text-blue-400' : 'text-gray-400 hover:text-white'}`}
        >
          <BarChart3 className="w-4 h-4" />
          Analytics
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'analytics' ? (
        <AnalyticsTab />
      ) : (
        <>
      {/* Client Info & Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Info Card */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
            <User className="w-5 h-5 text-gray-400" />
            Client Information
          </h3>
          <div className="space-y-3">
            <div>
              <p className="text-gray-500 text-xs">Status</p>
              <span className={`px-2 py-1 text-xs rounded-full ${
                client.status === 'active' ? 'bg-emerald-500/10 text-emerald-400' :
                client.status === 'frozen' ? 'bg-yellow-500/10 text-yellow-400' :
                'bg-red-500/10 text-red-400'
              }`}>
                {client.status}
              </span>
            </div>
            <div>
              <p className="text-gray-500 text-xs">Referral Code</p>
              <p className="text-emerald-400 font-mono">{client.referral_code}</p>
            </div>
            <div>
              <p className="text-gray-500 text-xs">Referred By</p>
              <p className="text-white">{client.referred_by_code || 'None'}</p>
            </div>
            <div>
              <p className="text-gray-500 text-xs">Joined</p>
              <p className="text-white text-sm">{new Date(client.created_at).toLocaleString()}</p>
            </div>
          </div>

          {/* Actions */}
          <div className="mt-6 space-y-2">
            <h4 className="text-gray-400 text-sm font-medium">Actions</h4>
            <div className="flex flex-wrap gap-2">
              {client.status !== 'banned' && (
                <button
                  onClick={() => handleStatusUpdate('banned')}
                  className="px-3 py-1.5 bg-red-500/10 text-red-400 rounded-lg text-sm hover:bg-red-500/20 transition flex items-center gap-1"
                >
                  <Ban className="w-4 h-4" /> Ban
                </button>
              )}
              {client.status === 'banned' && (
                <button
                  onClick={() => handleStatusUpdate('active')}
                  className="px-3 py-1.5 bg-emerald-500/10 text-emerald-400 rounded-lg text-sm hover:bg-emerald-500/20 transition flex items-center gap-1"
                >
                  <CheckCircle className="w-4 h-4" /> Unban
                </button>
              )}
              <button
                onClick={() => handleLockToggle('withdraw_locked', !client.withdraw_locked)}
                className={`px-3 py-1.5 rounded-lg text-sm transition flex items-center gap-1 ${
                  client.withdraw_locked ? 'bg-yellow-500/10 text-yellow-400' : 'bg-gray-700 text-gray-300'
                }`}
              >
                {client.withdraw_locked ? <Unlock className="w-4 h-4" /> : <Lock className="w-4 h-4" />}
                {client.withdraw_locked ? 'Unlock Withdraw' : 'Lock Withdraw'}
              </button>
            </div>
          </div>

          {/* Visibility Settings */}
          <div className="mt-6 space-y-2">
            <h4 className="text-gray-400 text-sm font-medium flex items-center gap-2">
              <Shield className="w-4 h-4" />
              Portal Visibility
            </h4>
            <div className="grid grid-cols-1 gap-2">
              <button
                onClick={() => handleVisibilityChange('full')}
                className={`px-3 py-2 rounded-lg text-sm transition flex items-center gap-2 ${
                  client.visibility_level === 'full' || !client.visibility_level
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                }`}
              >
                <Eye className="w-4 h-4" />
                Full Access
              </button>
              <button
                onClick={() => handleVisibilityChange('summary')}
                className={`px-3 py-2 rounded-lg text-sm transition flex items-center gap-2 ${
                  client.visibility_level === 'summary'
                    ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30'
                    : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                }`}
              >
                <Eye className="w-4 h-4" />
                Summary Only
              </button>
              <button
                onClick={() => handleVisibilityChange('hidden')}
                className={`px-3 py-2 rounded-lg text-sm transition flex items-center gap-2 ${
                  client.visibility_level === 'hidden'
                    ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                    : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                }`}
              >
                <EyeOff className="w-4 h-4" />
                Hidden
              </button>
            </div>
            <p className="text-gray-500 text-xs mt-1">
              Controls what the client can see in their portal
            </p>
          </div>
        </div>

        {/* Financial Summary */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
            <DollarSign className="w-5 h-5 text-gray-400" />
            Financial Summary
          </h3>
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-black border border-emerald-500/20 rounded-lg p-3">
              <p className="text-gray-500 text-xs">Total In</p>
              <p className="text-emerald-400 font-bold">${financial_summary.total_in?.toFixed(2)}</p>
            </div>
            <div className="bg-black border border-red-500/20 rounded-lg p-3">
              <p className="text-gray-500 text-xs">Total Out</p>
              <p className="text-red-400 font-bold">${financial_summary.total_out?.toFixed(2)}</p>
            </div>
            <div className="bg-black border border-gray-700 rounded-lg p-3">
              <p className="text-gray-500 text-xs">Net Balance</p>
              <p className="text-white font-bold">${financial_summary.net_balance?.toFixed(2)}</p>
            </div>
            <div className="bg-black border border-blue-500/20 rounded-lg p-3">
              <p className="text-gray-500 text-xs">Referral Earnings</p>
              <p className="text-blue-400 font-bold">${financial_summary.referral_earnings?.toFixed(2)}</p>
            </div>
          </div>
        </div>

        {/* Credentials */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-white font-semibold flex items-center gap-2">
              <Key className="w-5 h-5 text-gray-400" />
              Game Credentials
            </h3>
            <button
              onClick={() => setShowCredModal(true)}
              className="p-1.5 bg-emerald-500/10 text-emerald-400 rounded-lg hover:bg-emerald-500/20 transition"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>
          {credentials.length === 0 ? (
            <p className="text-gray-500 text-center py-4">No credentials assigned</p>
          ) : (
            <div className="space-y-2">
              {credentials.map((cred) => (
                <div key={cred.id} className="bg-black border border-gray-700 rounded-lg p-3">
                  <p className="text-white font-medium">{cred.game_name}</p>
                  <p className="text-gray-500 text-xs mt-1">
                    {cred.is_active ? (
                      <span className="text-emerald-400">Active</span>
                    ) : (
                      <span className="text-red-400">Inactive / Not Set</span>
                    )}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Recent Transactions */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h3 className="text-white font-semibold mb-4">Recent Transactions</h3>
        {recent_transactions.length === 0 ? (
          <p className="text-gray-500 text-center py-4">No transactions</p>
        ) : (
          <div className="space-y-2">
            {recent_transactions.map((tx) => (
              <div key={tx.transaction_id} className="flex items-center justify-between p-3 bg-black border border-gray-800 rounded-lg">
                <div className="flex items-center gap-3">
                  {tx.type === 'IN' ? (
                    <TrendingUp className="w-4 h-4 text-emerald-400" />
                  ) : (
                    <TrendingDown className="w-4 h-4 text-red-400" />
                  )}
                  <div>
                    <p className="text-white text-sm">{tx.type}</p>
                    <p className="text-gray-500 text-xs">{new Date(tx.created_at).toLocaleString()}</p>
                  </div>
                </div>
                <p className={`font-bold ${tx.type === 'OUT' ? 'text-red-400' : 'text-emerald-400'}`}>
                  ${tx.amount?.toFixed(2)}
                </p>
              </div>
            ))}
          </div>
        )}

        {/* CLIENT OVERRIDES SECTION */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-white font-semibold flex items-center gap-2">
              <Settings className="w-5 h-5 text-orange-400" />
              Client Overrides
            </h3>
            <button
              onClick={handleSaveOverrides}
              className="px-3 py-1.5 bg-emerald-500 text-white rounded-lg hover:bg-emerald-600 transition flex items-center gap-2 text-sm"
            >
              <Save className="w-4 h-4" />
              Save
            </button>
          </div>
          <p className="text-gray-500 text-xs mb-4">
            Custom rules for this client (overrides global and game rules)
          </p>

          <div className="space-y-4">
            {/* Custom Bonuses */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-gray-400 text-sm mb-1.5">
                  Custom Deposit Bonus %
                </label>
                <input
                  type="number"
                  placeholder="Leave empty for default"
                  value={overrides.custom_deposit_bonus || ''}
                  onChange={(e) => setOverrides({...overrides, custom_deposit_bonus: e.target.value ? parseFloat(e.target.value) : null})}
                  className="w-full px-3 py-2 bg-black border border-gray-700 rounded-lg text-white"
                  step="0.1"
                />
                <p className="text-gray-600 text-xs mt-1">
                  Example: 10 for 10% bonus
                </p>
              </div>
              
              <div>
                <label className="block text-gray-400 text-sm mb-1.5">
                  Custom Cashout Min Multiplier
                </label>
                <input
                  type="number"
                  placeholder="Leave empty for default"
                  value={overrides.custom_cashout_min || ''}
                  onChange={(e) => setOverrides({...overrides, custom_cashout_min: e.target.value ? parseFloat(e.target.value) : null})}
                  className="w-full px-3 py-2 bg-black border border-gray-700 rounded-lg text-white"
                  step="0.1"
                />
                <p className="text-gray-600 text-xs mt-1">
                  Example: 1.5 for 1.5x minimum
                </p>
              </div>
            </div>

            <div>
              <label className="block text-gray-400 text-sm mb-1.5">
                Custom Cashout Max Multiplier
              </label>
              <input
                type="number"
                placeholder="Leave empty for default"
                value={overrides.custom_cashout_max || ''}
                onChange={(e) => setOverrides({...overrides, custom_cashout_max: e.target.value ? parseFloat(e.target.value) : null})}
                className="w-full px-3 py-2 bg-black border border-gray-700 rounded-lg text-white"
                step="0.1"
              />
              <p className="text-gray-600 text-xs mt-1">
                Example: 3.0 for 3x maximum
              </p>
            </div>

            {/* Risk Flags */}
            <div className="pt-3 border-t border-gray-800">
              <p className="text-gray-400 text-sm font-medium mb-3">Risk Flags</p>
              <div className="space-y-2">
                <label className="flex items-center justify-between p-3 bg-black border border-gray-700 rounded-lg cursor-pointer hover:border-gray-600 transition">
                  <div className="flex items-center gap-3">
                    <AlertTriangle className="w-4 h-4 text-yellow-400" />
                    <div>
                      <p className="text-white text-sm">Manual Approval Required</p>
                      <p className="text-gray-500 text-xs">All transactions require admin approval</p>
                    </div>
                  </div>
                  <input
                    type="checkbox"
                    checked={overrides.manual_approval_required}
                    onChange={(e) => setOverrides({...overrides, manual_approval_required: e.target.checked})}
                    className="w-5 h-5 rounded border-gray-600 bg-gray-800 text-emerald-500"
                  />
                </label>

                <label className="flex items-center justify-between p-3 bg-black border border-gray-700 rounded-lg cursor-pointer hover:border-gray-600 transition">
                  <div className="flex items-center gap-3">
                    <XCircle className="w-4 h-4 text-red-400" />
                    <div>
                      <p className="text-white text-sm">Bonus Disabled</p>
                      <p className="text-gray-500 text-xs">No bonuses awarded on deposits</p>
                    </div>
                  </div>
                  <input
                    type="checkbox"
                    checked={overrides.bonus_disabled}
                    onChange={(e) => setOverrides({...overrides, bonus_disabled: e.target.checked})}
                    className="w-5 h-5 rounded border-gray-600 bg-gray-800 text-red-500"
                  />
                </label>

                <label className="flex items-center justify-between p-3 bg-black border border-gray-700 rounded-lg cursor-pointer hover:border-gray-600 transition">
                  <div className="flex items-center gap-3">
                    <Lock className="w-4 h-4 text-orange-400" />
                    <div>
                      <p className="text-white text-sm">Withdraw Disabled</p>
                      <p className="text-gray-500 text-xs">Client cannot initiate withdrawals</p>
                    </div>
                  </div>
                  <input
                    type="checkbox"
                    checked={overrides.withdraw_disabled}
                    onChange={(e) => setOverrides({...overrides, withdraw_disabled: e.target.checked})}
                    className="w-5 h-5 rounded border-gray-600 bg-gray-800 text-orange-500"
                  />
                </label>
              </div>
            </div>
          </div>
        </div>

        {/* ACTIVITY TIMELINE SECTION */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
            <Clock className="w-5 h-5 text-blue-400" />
            Activity Timeline
          </h3>
          
          {activityTimeline.length === 0 ? (
            <p className="text-gray-500 text-center py-8">No activity yet</p>
          ) : (
            <div className="space-y-3">
              {activityTimeline.map((activity, idx) => {
                let icon, color, bgColor;
                switch (activity.type) {
                  case 'signup':
                    icon = <User className="w-4 h-4" />;
                    color = 'text-blue-400';
                    bgColor = 'bg-blue-500/10';
                    break;
                  case 'deposit':
                    icon = <ArrowDown className="w-4 h-4" />;
                    color = 'text-emerald-400';
                    bgColor = 'bg-emerald-500/10';
                    break;
                  case 'withdrawal':
                    icon = <ArrowUp className="w-4 h-4" />;
                    color = 'text-red-400';
                    bgColor = 'bg-red-500/10';
                    break;
                  case 'bonus':
                    icon = <Gift className="w-4 h-4" />;
                    color = 'text-purple-400';
                    bgColor = 'bg-purple-500/10';
                    break;
                  case 'void':
                    icon = <XCircle className="w-4 h-4" />;
                    color = 'text-orange-400';
                    bgColor = 'bg-orange-500/10';
                    break;
                  case 'flag':
                    icon = <AlertTriangle className="w-4 h-4" />;
                    color = 'text-yellow-400';
                    bgColor = 'bg-yellow-500/10';
                    break;
                  default:
                    icon = <CheckCircle className="w-4 h-4" />;
                    color = 'text-gray-400';
                    bgColor = 'bg-gray-500/10';
                }

                return (
                  <div key={idx} className="flex items-start gap-3 relative">
                    {/* Timeline line */}
                    {idx < activityTimeline.length - 1 && (
                      <div className="absolute left-5 top-10 bottom-0 w-px bg-gray-800"></div>
                    )}
                    
                    {/* Icon */}
                    <div className={`${bgColor} ${color} p-2.5 rounded-lg flex-shrink-0 relative z-10`}>
                      {icon}
                    </div>
                    
                    {/* Content */}
                    <div className="flex-1 bg-black border border-gray-800 rounded-lg p-3">
                      <div className="flex items-start justify-between mb-1">
                        <p className="text-white font-medium text-sm">{activity.title}</p>
                        <span className="text-gray-500 text-xs">{new Date(activity.timestamp).toLocaleString()}</span>
                      </div>
                      <p className="text-gray-400 text-sm">{activity.description}</p>
                      {activity.amount && (
                        <p className={`text-sm font-semibold mt-1 ${activity.type === 'deposit' ? 'text-emerald-400' : activity.type === 'withdrawal' ? 'text-red-400' : 'text-purple-400'}`}>
                          ${activity.amount.toFixed(2)}
                        </p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
        </>
      )}

      {/* Credential Modal */}
      {showCredModal && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4" onClick={() => setShowCredModal(false)}>
          <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 w-full max-w-md" onClick={e => e.stopPropagation()}>
            <h3 className="text-xl font-bold text-white mb-4">Assign Credentials</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-gray-400 text-sm mb-1">Game</label>
                <select
                  value={credForm.game_id}
                  onChange={(e) => setCredForm({ ...credForm, game_id: e.target.value })}
                  className="w-full px-3 py-2 bg-black border border-gray-700 rounded-lg text-white"
                >
                  <option value="">Select Game</option>
                  {games.map(game => (
                    <option key={game.game_id || game.id} value={game.game_id || game.id}>
                      {game.display_name || game.game_name || game.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-gray-400 text-sm mb-1">Username</label>
                <input
                  type="text"
                  value={credForm.game_user_id}
                  onChange={(e) => setCredForm({ ...credForm, game_user_id: e.target.value })}
                  className="w-full px-3 py-2 bg-black border border-gray-700 rounded-lg text-white"
                />
              </div>
              <div>
                <label className="block text-gray-400 text-sm mb-1">Password</label>
                <input
                  type="text"
                  value={credForm.game_password}
                  onChange={(e) => setCredForm({ ...credForm, game_password: e.target.value })}
                  className="w-full px-3 py-2 bg-black border border-gray-700 rounded-lg text-white"
                />
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setShowCredModal(false)}
                  className="flex-1 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition"
                >
                  Cancel
                </button>
                <button
                  onClick={handleAssignCredential}
                  className="flex-1 py-2 bg-emerald-500 text-white rounded-lg hover:bg-emerald-600 transition"
                >
                  Assign
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminClientDetail;

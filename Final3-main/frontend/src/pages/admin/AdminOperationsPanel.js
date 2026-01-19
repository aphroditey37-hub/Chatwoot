/**
 * Admin Operations Panel
 * System automations and configuration
 * Uses centralized admin API client
 */
import React, { useEffect, useState, useCallback } from 'react';
import { toast } from 'sonner';
import {
  Settings, RefreshCw, Eye,
  DollarSign, Gamepad2,
  Shield, Zap, AlertTriangle, AlertCircle,
  Power, ArrowDownCircle,
  ArrowUpCircle, Clock, CheckCircle, XCircle, 
  List, Activity, Bot
} from 'lucide-react';

// Centralized Admin API
import { systemApi, dashboardApi, ordersApi, settingsApi, getErrorMessage } from '../../api/admin';

const AdminOperationsPanel = () => {
  const [activeTab, setActiveTab] = useState('overview');
  const [loading, setLoading] = useState(true);
  const [settings, setSettings] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);

  // Feature toggles
  const [featureToggles, setFeatureToggles] = useState({
    api_enabled: true,
    telegram_forwarding: false,
    manual_verification: true,
    auto_approve_loads: false,
    auto_approve_withdrawals: false,
    referral_system: true,
    bonus_system: true,
    webhook_notifications: true
  });

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [settingsRes, statsRes, txRes] = await Promise.all([
        settingsApi.get().catch(() => ({ data: {} })),
        dashboardApi.getSummary().catch(() => ({ data: {} })),
        ordersApi.getAll({ limit: 100 }).catch(() => ({ data: { orders: [] } }))
      ]);
      
      setSettings(settingsRes.data);
      setStats(statsRes.data);
      setTransactions(txRes.data.orders || []);
      
      // Load feature toggles from settings
      if (settingsRes.data.feature_toggles) {
        setFeatureToggles(prev => ({ ...prev, ...settingsRes.data.feature_toggles }));
      }
    } catch (err) {
      console.error('Failed to fetch data:', err);
      setError(getErrorMessage(err, 'Failed to load operations data'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleToggle = async (key) => {
    const newValue = !featureToggles[key];
    setFeatureToggles(prev => ({ ...prev, [key]: newValue }));
    
    try {
      await settingsApi.update({ feature_toggles: { [key]: newValue } });
      toast.success(`${key.replace(/_/g, ' ')} ${newValue ? 'enabled' : 'disabled'}`);
    } catch (err) {
      // Revert on error
      setFeatureToggles(prev => ({ ...prev, [key]: !newValue }));
      toast.error(getErrorMessage(err, 'Failed to update setting'));
    }
  };

  const getStatusBadge = (status) => {
    const styles = {
      pending: { bg: 'bg-yellow-500/20', text: 'text-yellow-400', icon: Clock },
      approved: { bg: 'bg-emerald-500/20', text: 'text-emerald-400', icon: CheckCircle },
      completed: { bg: 'bg-emerald-500/20', text: 'text-emerald-400', icon: CheckCircle },
      rejected: { bg: 'bg-red-500/20', text: 'text-red-400', icon: XCircle },
      failed: { bg: 'bg-red-500/20', text: 'text-red-400', icon: XCircle }
    };
    const style = styles[status] || styles.pending;
    const Icon = style.icon;
    
    return (
      <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${style.bg} ${style.text}`}>
        <Icon className="w-3 h-3" />
        {status?.charAt(0).toUpperCase() + status?.slice(1)}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 text-violet-500 animate-spin" />
      </div>
    );
  }

  if (error && !settings) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-3" />
          <p className="text-red-400 mb-4">{error}</p>
          <button 
            onClick={fetchData} 
            className="px-4 py-2 bg-violet-600 hover:bg-violet-500 rounded-lg text-white"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="operations-panel">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <Settings className="w-7 h-7 text-violet-400" />
            Operations & Automations
          </h1>
          <p className="text-gray-400 text-sm">Configure system automations and integrations</p>
        </div>
        <button
          onClick={fetchData}
          className="p-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition"
          data-testid="refresh-operations-btn"
        >
          <RefreshCw className={`w-5 h-5 text-gray-400 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Telegram Integration Banner */}
      <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-4">
        <div className="flex items-center gap-3">
          <Bot className="w-8 h-8 text-blue-400 flex-shrink-0" />
          <div className="flex-1">
            <h3 className="text-blue-400 font-bold">Telegram Bot Integration</h3>
            <p className="text-blue-300/80 text-sm">
              Configure Telegram bots for approvals and notifications in the dedicated Telegram Bots page.
            </p>
          </div>
          <a
            href="/admin/system/telegram-bots"
            className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition text-sm font-medium"
          >
            Manage Bots
          </a>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-gray-800 pb-2">
        {[
          { id: 'overview', label: 'Overview', icon: Activity },
          { id: 'features', label: 'Feature Toggles', icon: Power },
          { id: 'transactions', label: 'Recent Transactions', icon: List }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-t-lg font-medium transition ${
              activeTab === tab.id
                ? 'bg-violet-500/20 text-violet-400 border-b-2 border-violet-400'
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 bg-emerald-500/20 rounded-lg flex items-center justify-center">
                <ArrowDownCircle className="w-5 h-5 text-emerald-400" />
              </div>
              <span className="text-gray-400 text-sm">Deposits Today</span>
            </div>
            <div className="text-2xl font-bold text-white">{stats?.financial_summary?.deposits_today || 0}</div>
          </div>
          
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 bg-red-500/20 rounded-lg flex items-center justify-center">
                <ArrowUpCircle className="w-5 h-5 text-red-400" />
              </div>
              <span className="text-gray-400 text-sm">Withdrawals Today</span>
            </div>
            <div className="text-2xl font-bold text-white">{stats?.financial_summary?.withdrawals_today || 0}</div>
          </div>
          
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 bg-yellow-500/20 rounded-lg flex items-center justify-center">
                <Clock className="w-5 h-5 text-yellow-400" />
              </div>
              <span className="text-gray-400 text-sm">Pending</span>
            </div>
            <div className="text-2xl font-bold text-white">{stats?.pending_stats?.pending_payments || 0}</div>
          </div>
          
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 bg-purple-500/20 rounded-lg flex items-center justify-center">
                <Gamepad2 className="w-5 h-5 text-purple-400" />
              </div>
              <span className="text-gray-400 text-sm">Active Games</span>
            </div>
            <div className="text-2xl font-bold text-white">{stats?.games_count || 0}</div>
          </div>
        </div>
      )}

      {/* Feature Toggles Tab */}
      {activeTab === 'features' && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.entries(featureToggles).map(([key, value]) => {
              const labels = {
                api_enabled: { label: 'API Access', desc: 'Enable external API access', icon: Zap },
                telegram_forwarding: { label: 'Telegram Forwarding', desc: 'Forward events to Telegram', icon: Bot },
                manual_verification: { label: 'Manual Verification', desc: 'Require manual approval for payments', icon: Eye },
                auto_approve_loads: { label: 'Auto-Approve Loads', desc: 'Auto-approve wallet load requests', icon: CheckCircle },
                auto_approve_withdrawals: { label: 'Auto-Approve Withdrawals', desc: 'Auto-approve withdrawal requests', icon: ArrowUpCircle },
                referral_system: { label: 'Referral System', desc: 'Enable referral rewards', icon: DollarSign },
                bonus_system: { label: 'Bonus System', desc: 'Enable deposit bonuses', icon: DollarSign },
                webhook_notifications: { label: 'Webhooks', desc: 'Send webhook notifications', icon: Activity }
              };
              const config = labels[key] || { label: key, desc: '', icon: Settings };
              const Icon = config.icon;
              
              return (
                <div 
                  key={key}
                  className={`p-4 rounded-lg border ${value ? 'border-emerald-500/30 bg-emerald-500/5' : 'border-gray-700 bg-gray-800/50'}`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${value ? 'bg-emerald-500/20' : 'bg-gray-700'}`}>
                        <Icon className={`w-5 h-5 ${value ? 'text-emerald-400' : 'text-gray-500'}`} />
                      </div>
                      <div>
                        <p className="text-white font-medium">{config.label}</p>
                        <p className="text-gray-500 text-xs">{config.desc}</p>
                      </div>
                    </div>
                    <button
                      onClick={() => handleToggle(key)}
                      className={`relative w-12 h-6 rounded-full transition ${value ? 'bg-emerald-500' : 'bg-gray-600'}`}
                      data-testid={`toggle-${key}`}
                    >
                      <div className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-all ${value ? 'left-7' : 'left-1'}`} />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
          
          <div className="mt-6 p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-lg flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-yellow-400 font-medium">Caution</p>
              <p className="text-yellow-300/70 text-sm">
                Enabling auto-approve features will bypass manual review. Use with caution in production.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Transactions Tab */}
      {activeTab === 'transactions' && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-800">
            <h2 className="text-lg font-bold text-white">Recent Transactions</h2>
            <p className="text-gray-400 text-sm">Last 100 orders</p>
          </div>
          
          {transactions.length === 0 ? (
            <div className="text-center py-12">
              <List className="w-12 h-12 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-400">No transactions found</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-800 max-h-[500px] overflow-auto">
              {transactions.slice(0, 50).map(tx => (
                <div key={tx.order_id} className="p-4 hover:bg-gray-800/50 transition" data-testid={`tx-${tx.order_id}`}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                        tx.order_type === 'deposit' ? 'bg-emerald-500/20' : 'bg-red-500/20'
                      }`}>
                        {tx.order_type === 'deposit' ? (
                          <ArrowDownCircle className="w-5 h-5 text-emerald-400" />
                        ) : (
                          <ArrowUpCircle className="w-5 h-5 text-red-400" />
                        )}
                      </div>
                      <div>
                        <p className="text-white font-medium">{tx.display_name || tx.username}</p>
                        <p className="text-gray-500 text-xs">
                          {tx.order_type} • {new Date(tx.created_at).toLocaleString()}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <p className={`font-bold ${tx.order_type === 'deposit' ? 'text-emerald-400' : 'text-red-400'}`}>
                          ₱{tx.amount?.toFixed(2)}
                        </p>
                      </div>
                      {getStatusBadge(tx.status)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default AdminOperationsPanel;

/**
 * Telegram Bots Management Page
 * Manage multiple notification bots and their permissions
 * Uses centralized admin API client
 */
import React, { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import { 
  Bot, Plus, Edit3, Trash2, Check, X, RefreshCw, 
  ToggleLeft, ToggleRight, Shield,
  Bell, BellOff, TestTube, CheckCircle, XCircle, AlertCircle, Settings
} from 'lucide-react';

// Centralized Admin API
import { telegramApi, getErrorMessage } from '../../../api/admin';

const TelegramBots = () => {
  const [loading, setLoading] = useState(true);
  const [bots, setBots] = useState([]);
  const [events, setEvents] = useState([]);
  const [eventsByCategory, setEventsByCategory] = useState({});
  const [showModal, setShowModal] = useState(false);
  const [editingBot, setEditingBot] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [activeTab, setActiveTab] = useState('bots');
  const [testResult, setTestResult] = useState(null);
  const [error, setError] = useState(null);
  
  const [formData, setFormData] = useState({
    name: '',
    bot_token: '',
    chat_id: '',
    is_active: true,
    can_approve_payments: false,
    can_approve_wallet_loads: false,
    can_approve_withdrawals: false,
    description: ''
  });

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [botsRes, eventsRes] = await Promise.all([
        telegramApi.getBots(),
        telegramApi.getEvents()
      ]);
      setBots(botsRes.data.bots || []);
      setEvents(eventsRes.data.events || []);
      setEventsByCategory(eventsRes.data.by_category || {});
    } catch (err) {
      console.error('Failed to fetch data:', err);
      setError(getErrorMessage(err, 'Failed to load telegram bots'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleOpenModal = (bot = null) => {
    if (bot) {
      setEditingBot(bot);
      setFormData({
        name: bot.name,
        bot_token: '', // Don't show existing token
        chat_id: bot.chat_id,
        is_active: bot.is_active,
        can_approve_payments: bot.can_approve_payments,
        can_approve_wallet_loads: bot.can_approve_wallet_loads,
        can_approve_withdrawals: bot.can_approve_withdrawals,
        description: bot.description || ''
      });
    } else {
      setEditingBot(null);
      setFormData({
        name: '',
        bot_token: '',
        chat_id: '',
        is_active: true,
        can_approve_payments: false,
        can_approve_wallet_loads: false,
        can_approve_withdrawals: false,
        description: ''
      });
    }
    setShowModal(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.name || (!editingBot && !formData.bot_token) || !formData.chat_id) {
      toast.error('Please fill in all required fields');
      return;
    }

    setSubmitting(true);
    try {
      const payload = { ...formData };
      if (editingBot && !payload.bot_token) {
        delete payload.bot_token; // Don't send empty token on update
      }
      
      if (editingBot) {
        await telegramApi.updateBot(editingBot.bot_id, payload);
        toast.success('Bot updated successfully');
      } else {
        await telegramApi.createBot(payload);
        toast.success('Bot created successfully');
      }
      setShowModal(false);
      fetchData();
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to save bot'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (botId) => {
    if (!window.confirm('Are you sure you want to delete this bot? This will remove all its event permissions.')) return;
    
    try {
      await telegramApi.deleteBot(botId);
      toast.success('Bot deleted successfully');
      fetchData();
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to delete bot'));
    }
  };

  const handleToggleActive = async (bot) => {
    try {
      await telegramApi.updateBot(bot.bot_id, { is_active: !bot.is_active });
      toast.success(bot.is_active ? 'Bot disabled' : 'Bot enabled');
      fetchData();
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to update bot'));
    }
  };

  const handleTestBot = async (botId) => {
    setTestResult(null);
    try {
      const response = await telegramApi.testBot(botId);
      setTestResult({ botId, ...response.data });
      if (response.data.success) {
        toast.success('Test notification sent!');
      } else {
        toast.error(response.data.error || 'Test failed');
      }
    } catch (err) {
      const errorMsg = getErrorMessage(err, 'Test failed');
      setTestResult({ botId, success: false, error: errorMsg });
      toast.error(errorMsg);
    }
  };

  const handlePermissionChange = async (botId, eventType, enabled) => {
    try {
      await telegramApi.updateBotPermissions(botId, [{ event_type: eventType, enabled }]);
      fetchData();
    } catch (err) {
      console.error('Failed to update permission:', err);
      toast.error(getErrorMessage(err, 'Failed to update permission'));
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 text-emerald-500 animate-spin" />
      </div>
    );
  }

  if (error && bots.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-3" />
          <p className="text-red-400 mb-4">{error}</p>
          <button 
            onClick={fetchData} 
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-lg text-white"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="telegram-bots-management">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Telegram Bot Management</h1>
          <p className="text-gray-400 text-sm">Manage multiple notification bots and their permissions</p>
        </div>
        <div className="flex gap-2">
          <button onClick={fetchData} className="p-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition">
            <RefreshCw className={`w-5 h-5 text-gray-400 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={() => handleOpenModal()}
            className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg transition"
            data-testid="add-bot-btn"
          >
            <Plus className="w-5 h-5" />
            Add Bot
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-gray-800 pb-2">
        <button
          onClick={() => setActiveTab('bots')}
          className={`px-4 py-2 rounded-t-lg font-medium transition ${
            activeTab === 'bots' 
              ? 'bg-emerald-600 text-white' 
              : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
          }`}
          data-testid="tab-bots"
        >
          <Bot className="w-4 h-4 inline mr-2" />
          Bots ({bots.length})
        </button>
        <button
          onClick={() => setActiveTab('permissions')}
          className={`px-4 py-2 rounded-t-lg font-medium transition ${
            activeTab === 'permissions' 
              ? 'bg-emerald-600 text-white' 
              : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
          }`}
          data-testid="tab-permissions"
        >
          <Settings className="w-4 h-4 inline mr-2" />
          Event Permissions
        </button>
      </div>

      {/* Bots List Tab */}
      {activeTab === 'bots' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {bots.length === 0 ? (
            <div className="col-span-2 bg-gray-900 border border-gray-800 rounded-xl p-8 text-center">
              <Bot className="w-16 h-16 text-gray-600 mx-auto mb-4" />
              <h3 className="text-white font-medium mb-2">No Telegram Bots</h3>
              <p className="text-gray-400 text-sm mb-4">
                Add your first bot to start receiving notifications.
              </p>
              <button
                onClick={() => handleOpenModal()}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg transition"
              >
                Add Bot
              </button>
            </div>
          ) : (
            bots.map((bot) => (
              <div 
                key={bot.bot_id}
                className={`bg-gray-900 border rounded-xl p-6 ${
                  bot.is_active ? 'border-emerald-500/30' : 'border-gray-800'
                }`}
                data-testid={`bot-${bot.bot_id}`}
              >
                {/* Bot Header */}
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className={`p-3 rounded-xl ${bot.is_active ? 'bg-emerald-500/20' : 'bg-gray-700'}`}>
                      <Bot className={`w-6 h-6 ${bot.is_active ? 'text-emerald-400' : 'text-gray-500'}`} />
                    </div>
                    <div>
                      <h3 className="text-white font-bold">{bot.name}</h3>
                      <p className="text-gray-500 text-sm">Chat ID: {bot.chat_id}</p>
                    </div>
                  </div>
                  <span className={`px-2 py-1 text-xs rounded-full ${
                    bot.is_active 
                      ? 'bg-emerald-500/20 text-emerald-400' 
                      : 'bg-gray-600/20 text-gray-400'
                  }`}>
                    {bot.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>

                {/* Description */}
                {bot.description && (
                  <p className="text-gray-400 text-sm mb-4">{bot.description}</p>
                )}

                {/* Permissions Badges */}
                <div className="flex flex-wrap gap-2 mb-4">
                  {bot.can_approve_payments && (
                    <span className="px-2 py-1 bg-blue-500/20 text-blue-400 text-xs rounded-full flex items-center gap-1">
                      <Shield className="w-3 h-3" /> Payments
                    </span>
                  )}
                  {bot.can_approve_wallet_loads && (
                    <span className="px-2 py-1 bg-purple-500/20 text-purple-400 text-xs rounded-full flex items-center gap-1">
                      <Shield className="w-3 h-3" /> Wallet Loads
                    </span>
                  )}
                  {bot.can_approve_withdrawals && (
                    <span className="px-2 py-1 bg-orange-500/20 text-orange-400 text-xs rounded-full flex items-center gap-1">
                      <Shield className="w-3 h-3" /> Withdrawals
                    </span>
                  )}
                </div>

                {/* Event Count */}
                <div className="text-sm text-gray-500 mb-4">
                  {Object.values(bot.permissions || {}).filter(Boolean).length} events enabled
                </div>

                {/* Test Result */}
                {testResult && testResult.botId === bot.bot_id && (
                  <div className={`mb-4 p-3 rounded-lg ${
                    testResult.success 
                      ? 'bg-emerald-500/10 border border-emerald-500/30' 
                      : 'bg-red-500/10 border border-red-500/30'
                  }`}>
                    <div className="flex items-center gap-2">
                      {testResult.success ? (
                        <CheckCircle className="w-4 h-4 text-emerald-400" />
                      ) : (
                        <XCircle className="w-4 h-4 text-red-400" />
                      )}
                      <span className={testResult.success ? 'text-emerald-400' : 'text-red-400'}>
                        {testResult.success ? 'Test sent successfully!' : testResult.error}
                      </span>
                    </div>
                  </div>
                )}

                {/* Actions */}
                <div className="flex gap-2 flex-wrap">
                  <button
                    onClick={() => handleTestBot(bot.bot_id)}
                    className="flex-1 py-2 bg-blue-500/20 text-blue-400 rounded-lg hover:bg-blue-500/30 text-sm flex items-center justify-center gap-1"
                    data-testid={`test-bot-${bot.bot_id}`}
                  >
                    <TestTube className="w-4 h-4" />
                    Test
                  </button>
                  <button
                    onClick={() => handleToggleActive(bot)}
                    className={`flex-1 py-2 rounded-lg text-sm flex items-center justify-center gap-1 ${
                      bot.is_active 
                        ? 'bg-gray-700 text-gray-300 hover:bg-gray-600' 
                        : 'bg-emerald-600/20 text-emerald-400 hover:bg-emerald-600/30'
                    }`}
                    data-testid={`toggle-bot-${bot.bot_id}`}
                  >
                    {bot.is_active ? <ToggleRight className="w-4 h-4" /> : <ToggleLeft className="w-4 h-4" />}
                    {bot.is_active ? 'Disable' : 'Enable'}
                  </button>
                  <button
                    onClick={() => handleOpenModal(bot)}
                    className="py-2 px-3 bg-gray-700 text-gray-300 rounded-lg hover:bg-gray-600 text-sm"
                    data-testid={`edit-bot-${bot.bot_id}`}
                  >
                    <Edit3 className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleDelete(bot.bot_id)}
                    className="py-2 px-3 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 text-sm"
                    data-testid={`delete-bot-${bot.bot_id}`}
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Permissions Tab */}
      {activeTab === 'permissions' && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          {bots.length === 0 ? (
            <div className="p-8 text-center">
              <AlertCircle className="w-12 h-12 text-gray-600 mx-auto mb-4" />
              <p className="text-gray-400">Add a bot first to configure event permissions.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-800/50">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-400 sticky left-0 bg-gray-800/50">Event</th>
                    {bots.map(bot => (
                      <th key={bot.bot_id} className="px-4 py-3 text-center text-sm font-medium text-gray-400 min-w-[120px]">
                        <div className="flex flex-col items-center gap-1">
                          <span className={bot.is_active ? 'text-emerald-400' : 'text-gray-500'}>
                            {bot.name}
                          </span>
                          {!bot.is_active && (
                            <span className="text-xs text-gray-600">(disabled)</span>
                          )}
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(eventsByCategory).map(([category, categoryEvents]) => (
                    <React.Fragment key={category}>
                      {/* Category Header */}
                      <tr className="bg-gray-800/30">
                        <td colSpan={bots.length + 1} className="px-4 py-2">
                          <span className="text-sm font-bold text-gray-300">{category}</span>
                        </td>
                      </tr>
                      {/* Events */}
                      {categoryEvents.map(event => (
                        <tr key={event.event_type} className="border-t border-gray-800 hover:bg-gray-800/20">
                          <td className="px-4 py-3 sticky left-0 bg-gray-900">
                            <div>
                              <p className="text-white text-sm font-medium">{event.label}</p>
                              <p className="text-gray-500 text-xs">{event.description}</p>
                              {event.requires_approval && (
                                <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-yellow-500/20 text-yellow-400 text-xs rounded mt-1">
                                  <Shield className="w-3 h-3" /> Approval
                                </span>
                              )}
                            </div>
                          </td>
                          {bots.map(bot => {
                            const enabled = bot.permissions?.[event.event_type] || false;
                            return (
                              <td key={bot.bot_id} className="px-4 py-3 text-center">
                                <button
                                  onClick={() => handlePermissionChange(bot.bot_id, event.event_type, !enabled)}
                                  className={`w-10 h-10 rounded-lg flex items-center justify-center transition ${
                                    enabled 
                                      ? 'bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30' 
                                      : 'bg-gray-700 text-gray-500 hover:bg-gray-600'
                                  }`}
                                  disabled={!bot.is_active}
                                  title={enabled ? 'Disable' : 'Enable'}
                                  data-testid={`perm-${bot.bot_id}-${event.event_type}`}
                                >
                                  {enabled ? <Bell className="w-5 h-5" /> : <BellOff className="w-5 h-5" />}
                                </button>
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </React.Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Add/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4">
          <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 w-full max-w-md max-h-[90vh] overflow-auto">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-bold text-white">
                {editingBot ? 'Edit Bot' : 'Add Telegram Bot'}
              </h3>
              <button onClick={() => setShowModal(false)} className="text-gray-400 hover:text-white">
                <X className="w-6 h-6" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Bot Name *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g., Orders Bot, Approvals Bot"
                  className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white"
                  required
                  data-testid="bot-name-input"
                />
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-1">
                  Bot Token * {editingBot && <span className="text-gray-600">(leave empty to keep current)</span>}
                </label>
                <input
                  type="password"
                  value={formData.bot_token}
                  onChange={(e) => setFormData({ ...formData, bot_token: e.target.value })}
                  placeholder="123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
                  className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white font-mono text-sm"
                  required={!editingBot}
                  data-testid="bot-token-input"
                />
                <p className="text-xs text-gray-500 mt-1">Get this from @BotFather on Telegram</p>
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-1">Chat ID *</label>
                <input
                  type="text"
                  value={formData.chat_id}
                  onChange={(e) => setFormData({ ...formData, chat_id: e.target.value })}
                  placeholder="-1001234567890"
                  className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white font-mono"
                  required
                  data-testid="chat-id-input"
                />
                <p className="text-xs text-gray-500 mt-1">Group/channel ID where notifications will be sent</p>
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-1">Description</label>
                <input
                  type="text"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="e.g., Main operations bot"
                  className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white"
                  data-testid="bot-description-input"
                />
              </div>

              <div className="border-t border-gray-800 pt-4">
                <p className="text-sm text-gray-400 mb-3">Approval Permissions</p>
                <div className="space-y-3">
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formData.can_approve_payments}
                      onChange={(e) => setFormData({ ...formData, can_approve_payments: e.target.checked })}
                      className="w-4 h-4 rounded border-gray-600 text-emerald-600"
                    />
                    <span className="text-gray-300">Can approve deposit orders</span>
                  </label>
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formData.can_approve_wallet_loads}
                      onChange={(e) => setFormData({ ...formData, can_approve_wallet_loads: e.target.checked })}
                      className="w-4 h-4 rounded border-gray-600 text-purple-600"
                    />
                    <span className="text-gray-300">Can approve wallet loads</span>
                  </label>
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formData.can_approve_withdrawals}
                      onChange={(e) => setFormData({ ...formData, can_approve_withdrawals: e.target.checked })}
                      className="w-4 h-4 rounded border-gray-600 text-orange-600"
                    />
                    <span className="text-gray-300">Can approve withdrawals</span>
                  </label>
                </div>
              </div>

              <div className="flex items-center gap-3 pt-2">
                <input
                  type="checkbox"
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                  className="w-4 h-4 rounded border-gray-600 text-emerald-600"
                  id="is-active"
                />
                <label htmlFor="is-active" className="text-gray-300">Active (receive notifications)</label>
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="flex-1 py-2 bg-gray-800 text-gray-300 rounded-lg hover:bg-gray-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="flex-1 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:opacity-50 flex items-center justify-center gap-2"
                  data-testid="save-bot-btn"
                >
                  {submitting ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Check className="w-4 h-4" />
                      {editingBot ? 'Update' : 'Create'}
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default TelegramBots;

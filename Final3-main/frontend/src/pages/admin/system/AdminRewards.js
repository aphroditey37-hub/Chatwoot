/**
 * Admin Rewards Management Page
 * Define and manage automatic rewards for clients
 * Uses centralized admin API client
 */
import React, { useEffect, useState, useCallback } from 'react';
import { toast } from 'sonner';
import { 
  Gift, Plus, Edit, Trash2, RefreshCw, X, AlertCircle,
  Award, Eye, EyeOff
} from 'lucide-react';

// Centralized Admin API
import { rewardsAdminApi, getErrorMessage } from '../../../api/admin';

const AdminRewards = () => {
  const [loading, setLoading] = useState(true);
  const [rewards, setRewards] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [editingReward, setEditingReward] = useState(null);
  const [grantHistory, setGrantHistory] = useState([]);
  const [showHistoryModal, setShowHistoryModal] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    trigger_type: 'account_setup',
    reward_type: 'play_credits',
    value: 0,
    value_type: 'fixed',
    enabled: true,
    is_one_time: true,
    visible_to_client: true
  });

  const fetchRewards = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await rewardsAdminApi.getAll();
      setRewards(response.data.rewards || []);
    } catch (err) {
      console.error('Failed to fetch rewards:', err);
      setError(getErrorMessage(err, 'Failed to load rewards'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRewards();
  }, [fetchRewards]);

  const fetchGrantHistory = async () => {
    try {
      const response = await rewardsAdminApi.getGrantHistory(100);
      setGrantHistory(response.data.grants || []);
      setShowHistoryModal(true);
    } catch (err) {
      console.error('Failed to fetch grant history:', err);
      toast.error(getErrorMessage(err, 'Failed to load grant history'));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      if (editingReward) {
        await rewardsAdminApi.update(editingReward.reward_id, formData);
        toast.success('Reward updated successfully');
      } else {
        await rewardsAdminApi.create(formData);
        toast.success('Reward created successfully');
      }
      setShowModal(false);
      setEditingReward(null);
      resetForm();
      fetchRewards();
    } catch (err) {
      console.error('Failed to save reward:', err);
      toast.error(getErrorMessage(err, 'Failed to save reward'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (rewardId) => {
    if (!window.confirm('Are you sure you want to delete this reward?')) return;
    try {
      await rewardsAdminApi.delete(rewardId);
      toast.success('Reward deleted successfully');
      fetchRewards();
    } catch (err) {
      console.error('Failed to delete reward:', err);
      toast.error(getErrorMessage(err, 'Failed to delete reward'));
    }
  };

  const handleEdit = (reward) => {
    setEditingReward(reward);
    setFormData({
      name: reward.name,
      description: reward.description || '',
      trigger_type: reward.trigger_type,
      reward_type: reward.reward_type,
      value: reward.value,
      value_type: reward.value_type,
      enabled: reward.enabled,
      is_one_time: reward.is_one_time,
      visible_to_client: reward.visible_to_client
    });
    setShowModal(true);
  };

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      trigger_type: 'account_setup',
      reward_type: 'play_credits',
      value: 0,
      value_type: 'fixed',
      enabled: true,
      is_one_time: true,
      visible_to_client: true
    });
  };

  const getTriggerLabel = (trigger) => {
    const labels = {
      'account_setup': 'Account Setup',
      'first_login': 'First Login',
      'first_deposit': 'First Deposit',
      'custom': 'Custom / Manual'
    };
    return labels[trigger] || trigger;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-emerald-500" />
      </div>
    );
  }

  if (error && rewards.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-3" />
          <p className="text-red-400 mb-4">{error}</p>
          <button 
            onClick={fetchRewards} 
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-lg text-white"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="admin-rewards-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Gift className="w-6 h-6 text-purple-400" />
            Reward Management
          </h1>
          <p className="text-gray-400 text-sm">Define and manage automatic rewards for clients</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={fetchRewards}
            className="p-2 bg-gray-800 hover:bg-gray-700 text-gray-400 hover:text-white rounded-lg"
            data-testid="refresh-rewards-btn"
          >
            <RefreshCw className="w-5 h-5" />
          </button>
          <button
            onClick={fetchGrantHistory}
            className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded-lg flex items-center gap-2"
            data-testid="grant-history-btn"
          >
            <Award className="w-4 h-4" />
            Grant History
          </button>
          <button
            onClick={() => { resetForm(); setEditingReward(null); setShowModal(true); }}
            className="px-4 py-2 bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg flex items-center gap-2"
            data-testid="new-reward-btn"
          >
            <Plus className="w-4 h-4" />
            New Reward
          </button>
        </div>
      </div>

      {/* Info Banner */}
      <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-4">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-blue-400 font-medium">Automatic Reward System</p>
            <p className="text-gray-300 text-sm mt-1">
              Rewards are automatically granted when clients complete trigger actions. 
              All rewards are credited as <strong>Play Credits</strong> only (non-withdrawable).
            </p>
          </div>
        </div>
      </div>

      {/* Rewards Table */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-800/50">
            <tr>
              <th className="text-left text-gray-400 text-xs font-medium py-3 px-4">Reward</th>
              <th className="text-left text-gray-400 text-xs font-medium py-3 px-4">Trigger</th>
              <th className="text-left text-gray-400 text-xs font-medium py-3 px-4">Type</th>
              <th className="text-right text-gray-400 text-xs font-medium py-3 px-4">Value</th>
              <th className="text-center text-gray-400 text-xs font-medium py-3 px-4">Options</th>
              <th className="text-center text-gray-400 text-xs font-medium py-3 px-4">Granted</th>
              <th className="text-center text-gray-400 text-xs font-medium py-3 px-4">Status</th>
              <th className="text-right text-gray-400 text-xs font-medium py-3 px-4">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800">
            {rewards.length === 0 ? (
              <tr>
                <td colSpan="8" className="py-12 text-center text-gray-500">
                  <Gift className="w-12 h-12 mx-auto mb-3 text-gray-600" />
                  <p>No rewards defined yet</p>
                  <p className="text-sm">Create your first reward to incentivize clients</p>
                </td>
              </tr>
            ) : (
              rewards.map(reward => (
                <tr key={reward.reward_id} className="hover:bg-gray-800/30" data-testid={`reward-${reward.reward_id}`}>
                  <td className="py-3 px-4">
                    <div>
                      <p className="text-white font-medium">{reward.name}</p>
                      {reward.description && (
                        <p className="text-gray-500 text-xs mt-0.5">{reward.description}</p>
                      )}
                    </div>
                  </td>
                  <td className="py-3 px-4">
                    <span className="px-2 py-1 bg-purple-500/20 text-purple-400 text-xs rounded-full">
                      {getTriggerLabel(reward.trigger_type)}
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    <span className="text-gray-300 text-sm capitalize">{reward.reward_type?.replace('_', ' ')}</span>
                  </td>
                  <td className="py-3 px-4 text-right">
                    <span className="text-emerald-400 font-bold">
                      {reward.value_type === 'percentage' ? `${reward.value}%` : `$${reward.value}`}
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    <div className="flex items-center justify-center gap-2">
                      {reward.is_one_time && (
                        <span className="px-2 py-0.5 bg-yellow-500/20 text-yellow-400 text-xs rounded" title="One-time only">
                          1x
                        </span>
                      )}
                      {reward.visible_to_client ? (
                        <Eye className="w-4 h-4 text-gray-400" title="Visible to clients" />
                      ) : (
                        <EyeOff className="w-4 h-4 text-gray-600" title="Hidden from clients" />
                      )}
                    </div>
                  </td>
                  <td className="py-3 px-4 text-center">
                    <span className="text-white font-medium">{reward.grant_count || 0}</span>
                  </td>
                  <td className="py-3 px-4 text-center">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      reward.enabled 
                        ? 'bg-emerald-500/20 text-emerald-400' 
                        : 'bg-gray-700 text-gray-400'
                    }`}>
                      {reward.enabled ? 'Active' : 'Disabled'}
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => handleEdit(reward)}
                        className="p-1.5 text-gray-400 hover:text-white hover:bg-gray-700 rounded"
                        data-testid={`edit-reward-${reward.reward_id}`}
                      >
                        <Edit className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(reward.reward_id)}
                        className="p-1.5 text-gray-400 hover:text-red-400 hover:bg-red-500/10 rounded"
                        data-testid={`delete-reward-${reward.reward_id}`}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Create/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl w-full max-w-lg">
            <div className="p-4 border-b border-gray-800 flex items-center justify-between">
              <h3 className="text-lg font-bold text-white">
                {editingReward ? 'Edit Reward' : 'Create New Reward'}
              </h3>
              <button onClick={() => { setShowModal(false); setEditingReward(null); }} className="text-gray-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <form onSubmit={handleSubmit} className="p-4 space-y-4">
              <div>
                <label className="block text-gray-400 text-sm mb-1">Name *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({...formData, name: e.target.value})}
                  required
                  className="w-full px-3 py-2 bg-black border border-gray-700 rounded-lg text-white"
                  placeholder="Welcome Bonus"
                  data-testid="reward-name-input"
                />
              </div>

              <div>
                <label className="block text-gray-400 text-sm mb-1">Description</label>
                <input
                  type="text"
                  value={formData.description}
                  onChange={(e) => setFormData({...formData, description: e.target.value})}
                  className="w-full px-3 py-2 bg-black border border-gray-700 rounded-lg text-white"
                  placeholder="Reward for completing account setup"
                  data-testid="reward-description-input"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-gray-400 text-sm mb-1">Trigger Type *</label>
                  <select
                    value={formData.trigger_type}
                    onChange={(e) => setFormData({...formData, trigger_type: e.target.value})}
                    className="w-full px-3 py-2 bg-black border border-gray-700 rounded-lg text-white"
                    data-testid="trigger-type-select"
                  >
                    <option value="account_setup">Account Setup</option>
                    <option value="first_login">First Login</option>
                    <option value="first_deposit">First Deposit</option>
                    <option value="custom">Custom / Manual</option>
                  </select>
                </div>

                <div>
                  <label className="block text-gray-400 text-sm mb-1">Reward Type *</label>
                  <select
                    value={formData.reward_type}
                    onChange={(e) => setFormData({...formData, reward_type: e.target.value})}
                    className="w-full px-3 py-2 bg-black border border-gray-700 rounded-lg text-white"
                    data-testid="reward-type-select"
                  >
                    <option value="play_credits">Play Credits</option>
                    <option value="bonus">Bonus Balance</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-gray-400 text-sm mb-1">Value *</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={formData.value}
                    onChange={(e) => setFormData({...formData, value: parseFloat(e.target.value) || 0})}
                    required
                    className="w-full px-3 py-2 bg-black border border-gray-700 rounded-lg text-white"
                    data-testid="reward-value-input"
                  />
                </div>

                <div>
                  <label className="block text-gray-400 text-sm mb-1">Value Type</label>
                  <select
                    value={formData.value_type}
                    onChange={(e) => setFormData({...formData, value_type: e.target.value})}
                    className="w-full px-3 py-2 bg-black border border-gray-700 rounded-lg text-white"
                    data-testid="value-type-select"
                  >
                    <option value="fixed">Fixed Amount ($)</option>
                    <option value="percentage">Percentage (%)</option>
                  </select>
                </div>
              </div>

              {/* Toggles */}
              <div className="space-y-3">
                <label className="flex items-center justify-between p-3 bg-gray-800 rounded-lg cursor-pointer">
                  <span className="text-gray-300">Enabled</span>
                  <input
                    type="checkbox"
                    checked={formData.enabled}
                    onChange={(e) => setFormData({...formData, enabled: e.target.checked})}
                    className="sr-only"
                  />
                  <div className={`w-10 h-6 rounded-full transition ${formData.enabled ? 'bg-emerald-500' : 'bg-gray-600'}`}>
                    <div className={`w-4 h-4 bg-white rounded-full m-1 transition ${formData.enabled ? 'translate-x-4' : ''}`}></div>
                  </div>
                </label>

                <label className="flex items-center justify-between p-3 bg-gray-800 rounded-lg cursor-pointer">
                  <span className="text-gray-300">One-time Only</span>
                  <input
                    type="checkbox"
                    checked={formData.is_one_time}
                    onChange={(e) => setFormData({...formData, is_one_time: e.target.checked})}
                    className="sr-only"
                  />
                  <div className={`w-10 h-6 rounded-full transition ${formData.is_one_time ? 'bg-emerald-500' : 'bg-gray-600'}`}>
                    <div className={`w-4 h-4 bg-white rounded-full m-1 transition ${formData.is_one_time ? 'translate-x-4' : ''}`}></div>
                  </div>
                </label>

                <label className="flex items-center justify-between p-3 bg-gray-800 rounded-lg cursor-pointer">
                  <span className="text-gray-300">Visible to Client</span>
                  <input
                    type="checkbox"
                    checked={formData.visible_to_client}
                    onChange={(e) => setFormData({...formData, visible_to_client: e.target.checked})}
                    className="sr-only"
                  />
                  <div className={`w-10 h-6 rounded-full transition ${formData.visible_to_client ? 'bg-emerald-500' : 'bg-gray-600'}`}>
                    <div className={`w-4 h-4 bg-white rounded-full m-1 transition ${formData.visible_to_client ? 'translate-x-4' : ''}`}></div>
                  </div>
                </label>
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => { setShowModal(false); setEditingReward(null); }}
                  className="flex-1 px-4 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="flex-1 px-4 py-2 bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg font-semibold disabled:opacity-50 flex items-center justify-center gap-2"
                  data-testid="save-reward-btn"
                >
                  {submitting ? (
                    <RefreshCw className="w-4 h-4 animate-spin" />
                  ) : null}
                  {editingReward ? 'Update Reward' : 'Create Reward'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Grant History Modal */}
      {showHistoryModal && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl w-full max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
            <div className="p-4 border-b border-gray-800 flex items-center justify-between">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Award className="w-5 h-5 text-amber-400" />
                Reward Grant History
              </h3>
              <button onClick={() => setShowHistoryModal(false)} className="text-gray-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="overflow-auto flex-1">
              {grantHistory.length === 0 ? (
                <div className="p-8 text-center text-gray-500">
                  No grants recorded yet
                </div>
              ) : (
                <table className="w-full">
                  <thead className="bg-gray-800/50 sticky top-0">
                    <tr>
                      <th className="text-left text-gray-400 text-xs py-2 px-4">User</th>
                      <th className="text-left text-gray-400 text-xs py-2 px-4">Reward</th>
                      <th className="text-right text-gray-400 text-xs py-2 px-4">Amount</th>
                      <th className="text-left text-gray-400 text-xs py-2 px-4">By</th>
                      <th className="text-right text-gray-400 text-xs py-2 px-4">Date</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-800">
                    {grantHistory.map(grant => (
                      <tr key={grant.grant_id} className="hover:bg-gray-800/30">
                        <td className="py-2 px-4 text-white">{grant.username}</td>
                        <td className="py-2 px-4 text-gray-300">{grant.reward_name}</td>
                        <td className="py-2 px-4 text-right text-emerald-400">${grant.amount?.toFixed(2)}</td>
                        <td className="py-2 px-4 text-gray-400 text-sm">{grant.granted_by_username || 'Auto'}</td>
                        <td className="py-2 px-4 text-right text-gray-500 text-sm">
                          {grant.granted_at ? new Date(grant.granted_at).toLocaleString() : '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminRewards;

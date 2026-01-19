/**
 * AdminSettings - System Settings Management
 * 
 * Features:
 * - General settings
 * - Referral tier configuration
 * - Bonus milestones
 * - Anti-fraud settings
 */

import React, { useEffect, useState, useCallback } from 'react';
import { toast } from 'sonner';
import { 
  Settings, Users, Gift, Shield, Save, RefreshCw, Plus, Trash2, 
  Edit2, X, AlertTriangle, Check, Percent, Target, Award, Lock,
  DollarSign
} from 'lucide-react';

// Centralized Admin API
import { settingsApi, getErrorMessage } from '../../api';

const AdminSettings = () => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [settings, setSettings] = useState(null);
  const [activeTab, setActiveTab] = useState('general');
  
  // Edit modals
  const [showTierModal, setShowTierModal] = useState(false);
  const [showMilestoneModal, setShowMilestoneModal] = useState(false);
  const [editingTier, setEditingTier] = useState(null);
  const [editingMilestone, setEditingMilestone] = useState(null);

  const fetchSettings = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await settingsApi.get();
      setSettings(response.data);
    } catch (err) {
      const message = getErrorMessage(err, 'Failed to fetch settings');
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

  const saveGlobalSettings = async (updates) => {
    setSaving(true);
    try {
      await settingsApi.update(updates);
      await fetchSettings();
      toast.success('Settings saved successfully');
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to save settings'));
    } finally {
      setSaving(false);
    }
  };

  const saveTiers = async (tiers) => {
    setSaving(true);
    try {
      await settingsApi.updateReferralTiers(tiers);
      await fetchSettings();
      setShowTierModal(false);
      setEditingTier(null);
      toast.success('Referral tiers updated');
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to save tiers'));
    } finally {
      setSaving(false);
    }
  };

  const deleteTier = async (tierNumber) => {
    if (!window.confirm('Delete this tier?')) return;
    try {
      await settingsApi.removeTier(tierNumber);
      await fetchSettings();
      toast.success('Tier deleted');
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to delete tier'));
    }
  };

  const saveMilestones = async (milestones) => {
    setSaving(true);
    try {
      await settingsApi.updateBonusMilestones(milestones);
      await fetchSettings();
      setShowMilestoneModal(false);
      setEditingMilestone(null);
      toast.success('Milestones updated');
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to save milestones'));
    } finally {
      setSaving(false);
    }
  };

  const saveAntifraud = async (updates) => {
    setSaving(true);
    try {
      await settingsApi.updateAntiFraud(updates);
      await fetchSettings();
      toast.success('Anti-fraud settings saved');
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to save anti-fraud settings'));
    } finally {
      setSaving(false);
    }
  };

  const tabs = [
    { id: 'general', label: 'General', icon: Settings },
    { id: 'referrals', label: 'Referrals', icon: Users },
    { id: 'bonuses', label: 'Bonuses', icon: Gift },
    { id: 'antifraud', label: 'Anti-Fraud', icon: Shield },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-violet-500"></div>
      </div>
    );
  }

  if (error && !settings) {
    return (
      <div className="p-8 text-center">
        <AlertTriangle className="w-12 h-12 text-red-400 mx-auto mb-4" />
        <p className="text-red-400 mb-4">{error}</p>
        <button
          onClick={fetchSettings}
          className="px-4 py-2 bg-gray-800 text-white rounded-lg hover:bg-gray-700"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">System Settings</h1>
          <p className="text-gray-400 text-sm">Configure platform behavior</p>
        </div>
        <button
          onClick={fetchSettings}
          disabled={loading}
          className="p-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
        >
          <RefreshCw className={`w-5 h-5 text-gray-400 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-gray-800 pb-2">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              activeTab === tab.id
                ? 'bg-violet-500/20 text-violet-400'
                : 'text-gray-400 hover:text-white hover:bg-gray-800'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* General Settings */}
      {activeTab === 'general' && settings && (
        <div className="space-y-6">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 space-y-4">
            <h3 className="text-lg font-medium text-white">Platform Settings</h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-gray-400 mb-2">Min Deposit Amount</label>
                <input
                  type="number"
                  defaultValue={settings.min_deposit || 10}
                  className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white"
                  onBlur={(e) => saveGlobalSettings({ min_deposit: Number(e.target.value) })}
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-2">Max Deposit Amount</label>
                <input
                  type="number"
                  defaultValue={settings.max_deposit || 1000}
                  className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white"
                  onBlur={(e) => saveGlobalSettings({ max_deposit: Number(e.target.value) })}
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-2">Min Withdrawal Amount</label>
                <input
                  type="number"
                  defaultValue={settings.min_withdrawal || 20}
                  className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white"
                  onBlur={(e) => saveGlobalSettings({ min_withdrawal: Number(e.target.value) })}
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-2">Max Withdrawal Amount</label>
                <input
                  type="number"
                  defaultValue={settings.max_withdrawal || 500}
                  className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white"
                  onBlur={(e) => saveGlobalSettings({ max_withdrawal: Number(e.target.value) })}
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Referral Settings */}
      {activeTab === 'referrals' && settings && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-medium text-white">Referral Tiers</h3>
            <button
              onClick={() => { setEditingTier(null); setShowTierModal(true); }}
              className="flex items-center gap-2 px-4 py-2 bg-violet-600 hover:bg-violet-500 text-white rounded-lg text-sm"
            >
              <Plus className="w-4 h-4" /> Add Tier
            </button>
          </div>
          
          <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
            {(!settings.referral_tiers || settings.referral_tiers.length === 0) ? (
              <div className="p-8 text-center text-gray-500">
                <Users className="w-12 h-12 mx-auto mb-3 opacity-30" />
                No referral tiers configured
              </div>
            ) : (
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-800">
                    <th className="text-left text-gray-400 text-xs font-medium py-3 px-4">Tier</th>
                    <th className="text-left text-gray-400 text-xs font-medium py-3 px-4">Min Referrals</th>
                    <th className="text-left text-gray-400 text-xs font-medium py-3 px-4">Bonus Rate</th>
                    <th className="text-right text-gray-400 text-xs font-medium py-3 px-4">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {settings.referral_tiers.map((tier, idx) => (
                    <tr key={idx} className="border-b border-gray-800/50">
                      <td className="py-3 px-4 text-white">Tier {tier.tier_number || idx + 1}</td>
                      <td className="py-3 px-4 text-gray-300">{tier.min_referrals}</td>
                      <td className="py-3 px-4 text-emerald-400">{tier.bonus_rate}%</td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={() => { setEditingTier(tier); setShowTierModal(true); }}
                          className="p-1 text-gray-400 hover:text-white mr-2"
                        >
                          <Edit2 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => deleteTier(tier.tier_number || idx + 1)}
                          className="p-1 text-gray-400 hover:text-red-400"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {/* Bonus Settings */}
      {activeTab === 'bonuses' && settings && (
        <div className="space-y-6">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 space-y-4">
            <h3 className="text-lg font-medium text-white">Welcome Bonus</h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-gray-400 mb-2">Welcome Bonus Amount</label>
                <input
                  type="number"
                  defaultValue={settings.welcome_bonus_amount || 5}
                  className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white"
                  onBlur={(e) => saveGlobalSettings({ welcome_bonus_amount: Number(e.target.value) })}
                />
              </div>
              <div className="flex items-center">
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    defaultChecked={settings.welcome_bonus_enabled}
                    className="w-5 h-5 rounded bg-gray-800 border-gray-700"
                    onChange={(e) => saveGlobalSettings({ welcome_bonus_enabled: e.target.checked })}
                  />
                  <span className="text-gray-300">Enable Welcome Bonus</span>
                </label>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between">
            <h3 className="text-lg font-medium text-white">Bonus Milestones</h3>
            <button
              onClick={() => { setEditingMilestone(null); setShowMilestoneModal(true); }}
              className="flex items-center gap-2 px-4 py-2 bg-violet-600 hover:bg-violet-500 text-white rounded-lg text-sm"
            >
              <Plus className="w-4 h-4" /> Add Milestone
            </button>
          </div>

          <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
            {(!settings.bonus_milestones || settings.bonus_milestones.length === 0) ? (
              <div className="p-8 text-center text-gray-500">
                <Award className="w-12 h-12 mx-auto mb-3 opacity-30" />
                No bonus milestones configured
              </div>
            ) : (
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-800">
                    <th className="text-left text-gray-400 text-xs font-medium py-3 px-4">Milestone</th>
                    <th className="text-left text-gray-400 text-xs font-medium py-3 px-4">Target</th>
                    <th className="text-left text-gray-400 text-xs font-medium py-3 px-4">Reward</th>
                    <th className="text-right text-gray-400 text-xs font-medium py-3 px-4">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {settings.bonus_milestones.map((milestone, idx) => (
                    <tr key={idx} className="border-b border-gray-800/50">
                      <td className="py-3 px-4 text-white">{milestone.name || `Milestone ${idx + 1}`}</td>
                      <td className="py-3 px-4 text-gray-300">${milestone.target_amount}</td>
                      <td className="py-3 px-4 text-emerald-400">${milestone.reward_amount}</td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={() => { setEditingMilestone(milestone); setShowMilestoneModal(true); }}
                          className="p-1 text-gray-400 hover:text-white mr-2"
                        >
                          <Edit2 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => {
                            const updated = settings.bonus_milestones.filter((_, i) => i !== idx);
                            saveMilestones(updated);
                          }}
                          className="p-1 text-gray-400 hover:text-red-400"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {/* Anti-Fraud Settings */}
      {activeTab === 'antifraud' && settings && (
        <div className="space-y-6">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 space-y-4">
            <h3 className="text-lg font-medium text-white flex items-center gap-2">
              <Shield className="w-5 h-5 text-red-400" />
              Anti-Fraud Configuration
            </h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-gray-400 mb-2">Max Daily Deposits</label>
                <input
                  type="number"
                  defaultValue={settings.anti_fraud?.max_daily_deposits || 5}
                  className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white"
                  onBlur={(e) => saveAntifraud({ max_daily_deposits: Number(e.target.value) })}
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-2">Max Daily Withdrawals</label>
                <input
                  type="number"
                  defaultValue={settings.anti_fraud?.max_daily_withdrawals || 3}
                  className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white"
                  onBlur={(e) => saveAntifraud({ max_daily_withdrawals: Number(e.target.value) })}
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-2">Suspicious Amount Threshold</label>
                <input
                  type="number"
                  defaultValue={settings.anti_fraud?.suspicious_threshold || 1000}
                  className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white"
                  onBlur={(e) => saveAntifraud({ suspicious_threshold: Number(e.target.value) })}
                />
              </div>
              <div className="flex items-center">
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    defaultChecked={settings.anti_fraud?.require_proof}
                    className="w-5 h-5 rounded bg-gray-800 border-gray-700"
                    onChange={(e) => saveAntifraud({ require_proof: e.target.checked })}
                  />
                  <span className="text-gray-300">Require Payment Proof</span>
                </label>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tier Modal */}
      {showTierModal && (
        <TierModal
          tier={editingTier}
          onSave={(tier) => {
            const tiers = [...(settings.referral_tiers || [])];
            if (editingTier) {
              const idx = tiers.findIndex(t => t.tier_number === editingTier.tier_number);
              if (idx >= 0) tiers[idx] = tier;
            } else {
              tiers.push({ ...tier, tier_number: tiers.length + 1 });
            }
            saveTiers(tiers);
          }}
          onClose={() => { setShowTierModal(false); setEditingTier(null); }}
        />
      )}

      {/* Milestone Modal */}
      {showMilestoneModal && (
        <MilestoneModal
          milestone={editingMilestone}
          onSave={(milestone) => {
            const milestones = [...(settings.bonus_milestones || [])];
            if (editingMilestone) {
              const idx = milestones.findIndex(m => m.milestone_number === editingMilestone.milestone_number);
              if (idx >= 0) milestones[idx] = milestone;
            } else {
              milestones.push({ ...milestone, milestone_number: milestones.length + 1 });
            }
            saveMilestones(milestones);
          }}
          onClose={() => { setShowMilestoneModal(false); setEditingMilestone(null); }}
        />
      )}
    </div>
  );
};

// Tier Modal Component
const TierModal = ({ tier, onSave, onClose }) => {
  const [form, setForm] = useState({
    tier_number: tier?.tier_number || 1,
    min_referrals: tier?.min_referrals || 0,
    bonus_rate: tier?.bonus_rate || 10,
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 w-full max-w-md">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-medium text-white">
            {tier ? 'Edit Tier' : 'Add Tier'}
          </h3>
          <button onClick={onClose} className="p-1 text-gray-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-2">Minimum Referrals</label>
            <input
              type="number"
              value={form.min_referrals}
              onChange={(e) => setForm({ ...form, min_referrals: Number(e.target.value) })}
              className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-2">Bonus Rate (%)</label>
            <input
              type="number"
              value={form.bonus_rate}
              onChange={(e) => setForm({ ...form, bonus_rate: Number(e.target.value) })}
              className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white"
            />
          </div>
        </div>
        
        <div className="flex gap-3 mt-6">
          <button
            onClick={onClose}
            className="flex-1 py-2 bg-gray-800 text-white rounded-lg hover:bg-gray-700"
          >
            Cancel
          </button>
          <button
            onClick={() => onSave(form)}
            className="flex-1 py-2 bg-violet-600 text-white rounded-lg hover:bg-violet-500"
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
};

// Milestone Modal Component
const MilestoneModal = ({ milestone, onSave, onClose }) => {
  const [form, setForm] = useState({
    name: milestone?.name || '',
    target_amount: milestone?.target_amount || 100,
    reward_amount: milestone?.reward_amount || 10,
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 w-full max-w-md">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-medium text-white">
            {milestone ? 'Edit Milestone' : 'Add Milestone'}
          </h3>
          <button onClick={onClose} className="p-1 text-gray-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-2">Name</label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white"
              placeholder="e.g., First Deposit Bonus"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-2">Target Amount ($)</label>
            <input
              type="number"
              value={form.target_amount}
              onChange={(e) => setForm({ ...form, target_amount: Number(e.target.value) })}
              className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-2">Reward Amount ($)</label>
            <input
              type="number"
              value={form.reward_amount}
              onChange={(e) => setForm({ ...form, reward_amount: Number(e.target.value) })}
              className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white"
            />
          </div>
        </div>
        
        <div className="flex gap-3 mt-6">
          <button
            onClick={onClose}
            className="flex-1 py-2 bg-gray-800 text-white rounded-lg hover:bg-gray-700"
          >
            Cancel
          </button>
          <button
            onClick={() => onSave(form)}
            className="flex-1 py-2 bg-violet-600 text-white rounded-lg hover:bg-violet-500"
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
};

export default AdminSettings;

/**
 * Admin Referrals Page
 * Complete referral program management including:
 * - Referral dashboard & statistics
 * - Tier configuration (Starter to Ruby)
 * - Global campaign overrides
 * - Individual client overrides
 * - Referral ledger
 */
import React, { useEffect, useState, useCallback } from 'react';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { 
  RefreshCw, Share2, Users, DollarSign, TrendingUp, Star, Award, UserPlus, Gift, Crown,
  AlertCircle, Settings, Percent, Calendar, User, Plus, Edit2, Trash2, CheckCircle, Clock, Target
} from 'lucide-react';

// Centralized Admin API
import { referralsApi, referralTiersApi, usersApi, getErrorMessage } from '../../api/admin';

// Tier badge colors
const TIER_COLORS = {
  'Starter': 'bg-gray-600 text-gray-100',
  'Silver': 'bg-gray-400 text-gray-900',
  'Gold': 'bg-yellow-500 text-yellow-900',
  'Platinum': 'bg-purple-500 text-white',
  'Ruby': 'bg-red-500 text-white',
};

const AdminReferrals = () => {
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState(null);
  const [ledger, setLedger] = useState([]);
  const [tiers, setTiers] = useState([]);
  const [globalOverrides, setGlobalOverrides] = useState([]);
  const [activeGlobalOverride, setActiveGlobalOverride] = useState(null);
  const [clientOverrides, setClientOverrides] = useState([]);
  const [error, setError] = useState(null);
  
  // Modal states
  const [showGlobalModal, setShowGlobalModal] = useState(false);
  const [showClientModal, setShowClientModal] = useState(false);
  const [editingOverride, setEditingOverride] = useState(null);
  const [processing, setProcessing] = useState(false);
  
  // Form states
  const [globalForm, setGlobalForm] = useState({
    name: '',
    bonus_percentage: 20,
    start_date: '',
    end_date: '',
    description: '',
  });
  
  const [clientForm, setClientForm] = useState({
    user_id: '',
    username: '',
    bonus_percentage: 25,
    expires_at: '',
    reason: '',
  });
  
  // Client search
  const [clientSearch, setClientSearch] = useState('');
  const [clientSearchResults, setClientSearchResults] = useState([]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [dashRes, ledgerRes, tiersRes, globalRes, clientRes] = await Promise.all([
        referralsApi.getDashboard().catch(() => ({ data: {} })),
        referralsApi.getLedger().catch(() => ({ data: { ledger: [] } })),
        referralTiersApi.getTiers().catch(() => ({ data: { tiers: [] } })),
        referralTiersApi.getGlobalOverrides().catch(() => ({ data: { overrides: [], active_override: null } })),
        referralTiersApi.getClientOverrides().catch(() => ({ data: { overrides: [] } })),
      ]);
      
      setDashboard(dashRes.data);
      setLedger(ledgerRes.data.ledger || []);
      setTiers(tiersRes.data.tiers || []);
      setGlobalOverrides(globalRes.data.overrides || []);
      setActiveGlobalOverride(globalRes.data.active_override);
      setClientOverrides(clientRes.data.overrides || []);
    } catch (err) {
      console.error('Failed to fetch referrals:', err);
      setError(getErrorMessage(err, 'Failed to load referrals'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Search clients for override assignment
  const searchClients = async (query) => {
    if (query.length < 2) {
      setClientSearchResults([]);
      return;
    }
    try {
      const res = await usersApi.getAll({ search: query, limit: 5 });
      setClientSearchResults(res.data.clients || []);
    } catch (err) {
      console.error('Client search failed:', err);
    }
  };

  // Update tier percentage
  const handleUpdateTier = async (tier) => {
    setProcessing(true);
    try {
      await referralTiersApi.updateTier(tier.tier_id, {
        tier_name: tier.tier_name,
        min_referrals: tier.min_referrals,
        max_referrals: tier.max_referrals,
        bonus_percentage: tier.bonus_percentage,
        description: tier.description,
        is_active: tier.is_active,
      });
      toast.success(`${tier.tier_name} tier updated`);
      fetchData();
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to update tier'));
    } finally {
      setProcessing(false);
    }
  };

  // Create/update global override
  const handleSaveGlobalOverride = async (e) => {
    e.preventDefault();
    setProcessing(true);
    try {
      const data = {
        ...globalForm,
        start_date: new Date(globalForm.start_date).toISOString(),
        end_date: new Date(globalForm.end_date).toISOString(),
        is_active: true,
      };
      
      if (editingOverride) {
        await referralTiersApi.updateGlobalOverride(editingOverride.override_id, data);
        toast.success('Campaign updated');
      } else {
        await referralTiersApi.createGlobalOverride(data);
        toast.success('Campaign created');
      }
      
      setShowGlobalModal(false);
      setEditingOverride(null);
      setGlobalForm({ name: '', bonus_percentage: 20, start_date: '', end_date: '', description: '' });
      fetchData();
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to save campaign'));
    } finally {
      setProcessing(false);
    }
  };

  // Delete global override
  const handleDeleteGlobalOverride = async (overrideId) => {
    if (!window.confirm('Delete this campaign?')) return;
    try {
      await referralTiersApi.deleteGlobalOverride(overrideId);
      toast.success('Campaign deleted');
      fetchData();
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to delete'));
    }
  };

  // Create/update client override
  const handleSaveClientOverride = async (e) => {
    e.preventDefault();
    setProcessing(true);
    try {
      const data = {
        user_id: clientForm.user_id,
        bonus_percentage: clientForm.bonus_percentage,
        expires_at: clientForm.expires_at ? new Date(clientForm.expires_at).toISOString() : null,
        reason: clientForm.reason,
      };
      
      if (editingOverride) {
        await referralTiersApi.updateClientOverride(clientForm.user_id, data);
        toast.success('Override updated');
      } else {
        await referralTiersApi.createClientOverride(data);
        toast.success('Override created');
      }
      
      setShowClientModal(false);
      setEditingOverride(null);
      setClientForm({ user_id: '', username: '', bonus_percentage: 25, expires_at: '', reason: '' });
      fetchData();
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to save override'));
    } finally {
      setProcessing(false);
    }
  };

  // Delete client override
  const handleDeleteClientOverride = async (userId) => {
    if (!window.confirm('Remove this override? Client will revert to tier-based percentage.')) return;
    try {
      await referralTiersApi.deleteClientOverride(userId);
      toast.success('Override removed');
      fetchData();
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to remove'));
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-emerald-500" />
      </div>
    );
  }

  if (error && !dashboard) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-3" />
          <p className="text-red-400 mb-4">{error}</p>
          <button onClick={fetchData} className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-lg text-white">
            Try Again
          </button>
        </div>
      </div>
    );
  }

  const topReferrer = dashboard?.top_referrers?.[0];

  return (
    <div className="space-y-6" data-testid="referrals-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-2">
            <Share2 className="w-7 h-7 text-purple-400" />
            Referral Program
          </h1>
          <p className="text-gray-400 mt-1">Manage tiers, overrides, and track growth</p>
        </div>
        <button onClick={fetchData} className="p-2.5 bg-gray-800 hover:bg-gray-700 rounded-xl text-gray-400 hover:text-white transition-all" data-testid="refresh-referrals-btn">
          <RefreshCw className="w-5 h-5" />
        </button>
      </div>

      {/* Active Global Campaign Banner */}
      {activeGlobalOverride && (
        <div className="bg-gradient-to-r from-purple-600/20 to-pink-600/20 border border-purple-500/30 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-purple-500/30 rounded-lg">
                <Target className="w-6 h-6 text-purple-400" />
              </div>
              <div>
                <p className="text-purple-300 font-semibold">Active Campaign: {activeGlobalOverride.name}</p>
                <p className="text-gray-400 text-sm">All referrers earning {activeGlobalOverride.bonus_percentage}% during this promotion</p>
              </div>
            </div>
            <div className="text-right">
              <p className="text-purple-400 font-bold text-2xl">{activeGlobalOverride.bonus_percentage}%</p>
              <p className="text-gray-500 text-xs">Override Active</p>
            </div>
          </div>
        </div>
      )}

      {/* Stats Overview */}
      <div className="grid grid-cols-4 gap-4">
        <Card className="bg-gray-900 border-gray-800">
          <CardContent className="pt-4">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-emerald-500/10 rounded-xl">
                <UserPlus className="w-6 h-6 text-emerald-400" />
              </div>
              <div>
                <p className="text-gray-400 text-sm">Total Referred</p>
                <p className="text-2xl font-bold text-white">{dashboard?.stats?.total_referred_users || 0}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-gray-900 border-gray-800">
          <CardContent className="pt-4">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-blue-500/10 rounded-xl">
                <Users className="w-6 h-6 text-blue-400" />
              </div>
              <div>
                <p className="text-gray-400 text-sm">Active Referrers</p>
                <p className="text-2xl font-bold text-white">{dashboard?.stats?.active_referrers || 0}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-gray-900 border-gray-800">
          <CardContent className="pt-4">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-purple-500/10 rounded-xl">
                <DollarSign className="w-6 h-6 text-purple-400" />
              </div>
              <div>
                <p className="text-gray-400 text-sm">Total Commission</p>
                <p className="text-2xl font-bold text-white">${(dashboard?.stats?.total_commission_earned || 0).toFixed(2)}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-gray-900 border-gray-800">
          <CardContent className="pt-4">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-orange-500/10 rounded-xl">
                <TrendingUp className="w-6 h-6 text-orange-400" />
              </div>
              <div>
                <p className="text-gray-400 text-sm">Client Overrides</p>
                <p className="text-2xl font-bold text-white">{clientOverrides.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Top Performer Spotlight */}
      {topReferrer && (
        <Card className="bg-gradient-to-br from-yellow-500/10 to-orange-500/10 border-yellow-500/30">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="relative">
                  <div className="w-16 h-16 bg-gradient-to-br from-yellow-400 to-orange-500 rounded-full flex items-center justify-center">
                    <Crown className="w-8 h-8 text-white" />
                  </div>
                  <div className="absolute -top-1 -right-1 w-6 h-6 bg-yellow-400 rounded-full flex items-center justify-center border-2 border-gray-900">
                    <span className="text-gray-900 text-xs font-bold">1</span>
                  </div>
                </div>
                <div>
                  <p className="text-yellow-400 text-xs font-semibold uppercase tracking-wide mb-1">Top Referrer</p>
                  <p className="text-white font-bold text-2xl">{topReferrer.username}</p>
                  <p className="text-gray-400 text-sm font-mono mt-1">Code: {topReferrer.referral_code}</p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-gray-400 text-sm mb-1">Total Referrals</p>
                <p className="text-yellow-400 font-bold text-3xl">{topReferrer.referral_count}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Tabs */}
      <Tabs defaultValue="tiers" className="space-y-4">
        <TabsList className="bg-gray-900 border border-gray-800">
          <TabsTrigger value="tiers" className="data-[state=active]:bg-purple-500/20 data-[state=active]:text-purple-300">
            <Award className="w-4 h-4 mr-2" />
            Tier Configuration
          </TabsTrigger>
          <TabsTrigger value="campaigns" className="data-[state=active]:bg-purple-500/20 data-[state=active]:text-purple-300">
            <Target className="w-4 h-4 mr-2" />
            Campaigns
          </TabsTrigger>
          <TabsTrigger value="overrides" className="data-[state=active]:bg-purple-500/20 data-[state=active]:text-purple-300">
            <User className="w-4 h-4 mr-2" />
            Client Overrides
          </TabsTrigger>
          <TabsTrigger value="top" className="data-[state=active]:bg-purple-500/20 data-[state=active]:text-purple-300">
            <Star className="w-4 h-4 mr-2" />
            Top Referrers
          </TabsTrigger>
          <TabsTrigger value="ledger" className="data-[state=active]:bg-purple-500/20 data-[state=active]:text-purple-300">
            <Gift className="w-4 h-4 mr-2" />
            Ledger
          </TabsTrigger>
        </TabsList>

        {/* Tier Configuration */}
        <TabsContent value="tiers">
          <Card className="bg-gray-900 border-gray-800">
            <CardHeader>
              <CardTitle className="text-lg text-white flex items-center gap-2">
                <Settings className="w-5 h-5 text-purple-400" />
                Referral Tier Percentages
              </CardTitle>
              <p className="text-gray-400 text-sm">Configure bonus percentages for each tier level</p>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {tiers.map((tier) => (
                  <div key={tier.tier_id} className="flex items-center justify-between p-4 bg-gray-800/50 rounded-xl border border-gray-700">
                    <div className="flex items-center gap-4">
                      <span className={`px-3 py-1 rounded-full text-sm font-semibold ${TIER_COLORS[tier.tier_name] || 'bg-gray-600 text-white'}`}>
                        {tier.tier_name}
                      </span>
                      <div>
                        <p className="text-white font-medium">{tier.min_referrals}{tier.max_referrals ? `-${tier.max_referrals}` : '+'} referrals</p>
                        <p className="text-gray-500 text-sm">{tier.description}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="flex items-center gap-2">
                        <Percent className="w-4 h-4 text-gray-400" />
                        <input
                          type="number"
                          value={tier.bonus_percentage}
                          onChange={(e) => {
                            const newTiers = [...tiers];
                            const idx = newTiers.findIndex(t => t.tier_id === tier.tier_id);
                            newTiers[idx] = { ...tier, bonus_percentage: parseFloat(e.target.value) || 0 };
                            setTiers(newTiers);
                          }}
                          className="w-20 px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-center"
                          min="0"
                          max="100"
                        />
                        <span className="text-gray-400">%</span>
                      </div>
                      <button
                        onClick={() => handleUpdateTier(tier)}
                        disabled={processing}
                        className="px-4 py-2 bg-purple-500 hover:bg-purple-600 text-white rounded-lg transition disabled:opacity-50"
                        data-testid={`save-tier-${tier.tier_id}`}
                      >
                        Save
                      </button>
                    </div>
                  </div>
                ))}
              </div>
              
              <div className="mt-6 p-4 bg-purple-500/10 border border-purple-500/30 rounded-xl">
                <p className="text-purple-300 text-sm">
                  <strong>Priority:</strong> Individual Override → Global Campaign → Tier-based percentage
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Campaigns (Global Overrides) */}
        <TabsContent value="campaigns">
          <Card className="bg-gray-900 border-gray-800">
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-lg text-white flex items-center gap-2">
                  <Target className="w-5 h-5 text-pink-400" />
                  Global Bonus Campaigns
                </CardTitle>
                <p className="text-gray-400 text-sm">Time-limited promotions that override tier percentages for all users</p>
              </div>
              <button
                onClick={() => {
                  setEditingOverride(null);
                  setGlobalForm({ name: '', bonus_percentage: 20, start_date: '', end_date: '', description: '' });
                  setShowGlobalModal(true);
                }}
                className="flex items-center gap-2 px-4 py-2 bg-pink-500 hover:bg-pink-600 text-white rounded-lg transition"
                data-testid="add-campaign-btn"
              >
                <Plus className="w-4 h-4" />
                New Campaign
              </button>
            </CardHeader>
            <CardContent>
              {globalOverrides.length === 0 ? (
                <div className="py-12 text-center">
                  <Target className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                  <p className="text-gray-500">No campaigns created yet</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {globalOverrides.map((o) => {
                    const isActive = activeGlobalOverride?.override_id === o.override_id;
                    const now = new Date();
                    const startDate = new Date(o.start_date);
                    const endDate = new Date(o.end_date);
                    const isPast = endDate < now;
                    const isFuture = startDate > now;
                    
                    return (
                      <div key={o.override_id} className={`p-4 rounded-xl border ${isActive ? 'bg-purple-500/10 border-purple-500/30' : 'bg-gray-800/50 border-gray-700'}`}>
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            {isActive ? (
                              <CheckCircle className="w-5 h-5 text-green-400" />
                            ) : isPast ? (
                              <Clock className="w-5 h-5 text-gray-500" />
                            ) : (
                              <Calendar className="w-5 h-5 text-blue-400" />
                            )}
                            <div>
                              <p className="text-white font-semibold">{o.name}</p>
                              <p className="text-gray-500 text-sm">{o.description || 'No description'}</p>
                            </div>
                          </div>
                          <div className="flex items-center gap-4">
                            <div className="text-right">
                              <p className="text-purple-400 font-bold">{o.bonus_percentage}%</p>
                              <p className="text-gray-500 text-xs">
                                {new Date(o.start_date).toLocaleDateString()} - {new Date(o.end_date).toLocaleDateString()}
                              </p>
                            </div>
                            <span className={`px-2 py-1 text-xs rounded-full ${
                              isActive ? 'bg-green-500/20 text-green-400' :
                              isPast ? 'bg-gray-500/20 text-gray-400' :
                              'bg-blue-500/20 text-blue-400'
                            }`}>
                              {isActive ? 'Active' : isPast ? 'Ended' : 'Scheduled'}
                            </span>
                            <button
                              onClick={() => {
                                setEditingOverride(o);
                                setGlobalForm({
                                  name: o.name,
                                  bonus_percentage: o.bonus_percentage,
                                  start_date: o.start_date.slice(0, 16),
                                  end_date: o.end_date.slice(0, 16),
                                  description: o.description || '',
                                });
                                setShowGlobalModal(true);
                              }}
                              className="p-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-gray-300"
                            >
                              <Edit2 className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => handleDeleteGlobalOverride(o.override_id)}
                              className="p-2 bg-red-500/20 hover:bg-red-500/30 rounded-lg text-red-400"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Client Overrides */}
        <TabsContent value="overrides">
          <Card className="bg-gray-900 border-gray-800">
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-lg text-white flex items-center gap-2">
                  <User className="w-5 h-5 text-emerald-400" />
                  Individual Client Overrides
                </CardTitle>
                <p className="text-gray-400 text-sm">Custom bonus percentages for specific clients (highest priority)</p>
              </div>
              <button
                onClick={() => {
                  setEditingOverride(null);
                  setClientForm({ user_id: '', username: '', bonus_percentage: 25, expires_at: '', reason: '' });
                  setClientSearch('');
                  setClientSearchResults([]);
                  setShowClientModal(true);
                }}
                className="flex items-center gap-2 px-4 py-2 bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg transition"
                data-testid="add-client-override-btn"
              >
                <Plus className="w-4 h-4" />
                Add Override
              </button>
            </CardHeader>
            <CardContent>
              {clientOverrides.length === 0 ? (
                <div className="py-12 text-center">
                  <User className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                  <p className="text-gray-500">No client overrides configured</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {clientOverrides.map((o) => (
                    <div key={o.override_id} className="flex items-center justify-between p-4 bg-gray-800/50 rounded-xl border border-gray-700">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-emerald-500/20 rounded-full flex items-center justify-center">
                          <User className="w-5 h-5 text-emerald-400" />
                        </div>
                        <div>
                          <p className="text-white font-semibold">{o.display_name || o.username}</p>
                          <p className="text-gray-500 text-sm">@{o.username}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        <div className="text-right">
                          <p className="text-emerald-400 font-bold">{o.bonus_percentage}%</p>
                          <p className="text-gray-500 text-xs">
                            {o.expires_at ? `Expires: ${new Date(o.expires_at).toLocaleDateString()}` : 'No expiry'}
                          </p>
                        </div>
                        <span className={`px-2 py-1 text-xs rounded-full ${o.is_active ? 'bg-green-500/20 text-green-400' : 'bg-gray-500/20 text-gray-400'}`}>
                          {o.is_active ? 'Active' : 'Inactive'}
                        </span>
                        <button
                          onClick={() => {
                            setEditingOverride(o);
                            setClientForm({
                              user_id: o.user_id,
                              username: o.username,
                              bonus_percentage: o.bonus_percentage,
                              expires_at: o.expires_at ? o.expires_at.slice(0, 16) : '',
                              reason: o.reason || '',
                            });
                            setShowClientModal(true);
                          }}
                          className="p-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-gray-300"
                        >
                          <Edit2 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDeleteClientOverride(o.user_id)}
                          className="p-2 bg-red-500/20 hover:bg-red-500/30 rounded-lg text-red-400"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Top Referrers */}
        <TabsContent value="top">
          <Card className="bg-gray-900 border-gray-800">
            <CardHeader>
              <CardTitle className="text-lg text-white flex items-center gap-2">
                <Award className="w-5 h-5 text-yellow-400" />
                Top Performers
              </CardTitle>
            </CardHeader>
            <CardContent>
              {dashboard?.top_referrers?.length === 0 ? (
                <div className="py-12 text-center">
                  <Users className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                  <p className="text-gray-500">No referrers yet</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {dashboard?.top_referrers?.map((r, i) => {
                    const isTop3 = i < 3;
                    const medalColors = ['from-yellow-400 to-orange-500', 'from-gray-300 to-gray-400', 'from-amber-600 to-amber-700'];
                    return (
                      <div key={i} className={`flex items-center justify-between p-4 rounded-xl transition-all ${isTop3 ? 'bg-gradient-to-r from-gray-800 to-gray-800/50 border border-gray-700' : 'bg-gray-800/50 hover:bg-gray-800'}`} data-testid={`referrer-${i}`}>
                        <div className="flex items-center gap-4 flex-1">
                          {isTop3 ? (
                            <div className={`w-10 h-10 bg-gradient-to-br ${medalColors[i]} rounded-full flex items-center justify-center shadow-lg`}>
                              <span className="text-white font-bold text-sm">{i + 1}</span>
                            </div>
                          ) : (
                            <div className="w-10 h-10 bg-gray-700 rounded-full flex items-center justify-center">
                              <span className="text-gray-400 font-mono text-sm">#{i + 1}</span>
                            </div>
                          )}
                          <div className="flex-1">
                            <p className="text-white font-semibold">{r.username}</p>
                            <p className="text-gray-500 text-sm font-mono">{r.referral_code}</p>
                          </div>
                          <div className="text-right">
                            <p className="text-purple-400 font-bold text-lg">{r.referral_count}</p>
                            <p className="text-gray-500 text-xs">referrals</p>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Ledger */}
        <TabsContent value="ledger">
          <Card className="bg-gray-900 border-gray-800">
            <CardHeader>
              <CardTitle className="text-lg text-white">Complete Referral History</CardTitle>
            </CardHeader>
            <CardContent>
              {ledger.length === 0 ? (
                <div className="py-12 text-center">
                  <Gift className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                  <p className="text-gray-500">No referral history yet</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-gray-800">
                        <th className="text-left text-gray-400 text-xs py-3 px-4 font-semibold uppercase">User</th>
                        <th className="text-left text-gray-400 text-xs py-3 px-4 font-semibold uppercase">Referrer</th>
                        <th className="text-left text-gray-400 text-xs py-3 px-4 font-semibold uppercase">Code</th>
                        <th className="text-right text-gray-400 text-xs py-3 px-4 font-semibold uppercase">Joined</th>
                      </tr>
                    </thead>
                    <tbody>
                      {ledger.map((r, i) => (
                        <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                          <td className="py-3 px-4 text-white">{r.user}</td>
                          <td className="py-3 px-4">
                            <div className="flex items-center gap-2">
                              <Star className="w-3 h-3 text-purple-400" />
                              <span className="text-purple-400 font-medium">{r.referrer}</span>
                            </div>
                          </td>
                          <td className="py-3 px-4">
                            <span className="px-2 py-1 bg-gray-800 rounded text-gray-400 text-sm font-mono">{r.referral_code}</span>
                          </td>
                          <td className="py-3 px-4 text-right text-gray-400 text-sm">
                            {r.created_at ? new Date(r.created_at).toLocaleDateString() : 'N/A'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Global Campaign Modal */}
      {showGlobalModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-lg mx-4">
            <div className="px-6 py-4 border-b border-gray-800">
              <h3 className="text-lg font-bold text-white">{editingOverride ? 'Edit Campaign' : 'New Campaign'}</h3>
            </div>
            <form onSubmit={handleSaveGlobalOverride} className="p-6 space-y-4">
              <div>
                <label className="block text-gray-400 text-sm mb-2">Campaign Name</label>
                <input type="text" required value={globalForm.name} onChange={(e) => setGlobalForm(f => ({ ...f, name: e.target.value }))} className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white" placeholder="Summer Bonus Bash" />
              </div>
              <div>
                <label className="block text-gray-400 text-sm mb-2">Bonus Percentage</label>
                <div className="flex items-center gap-2">
                  <input type="number" required value={globalForm.bonus_percentage} onChange={(e) => setGlobalForm(f => ({ ...f, bonus_percentage: parseFloat(e.target.value) || 0 }))} className="w-24 px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-center" min="0" max="100" />
                  <span className="text-gray-400">%</span>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-gray-400 text-sm mb-2">Start Date</label>
                  <input type="datetime-local" required value={globalForm.start_date} onChange={(e) => setGlobalForm(f => ({ ...f, start_date: e.target.value }))} className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white" />
                </div>
                <div>
                  <label className="block text-gray-400 text-sm mb-2">End Date</label>
                  <input type="datetime-local" required value={globalForm.end_date} onChange={(e) => setGlobalForm(f => ({ ...f, end_date: e.target.value }))} className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white" />
                </div>
              </div>
              <div>
                <label className="block text-gray-400 text-sm mb-2">Description (Optional)</label>
                <textarea value={globalForm.description} onChange={(e) => setGlobalForm(f => ({ ...f, description: e.target.value }))} className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white" rows={2} placeholder="Special summer promotion..." />
              </div>
              <div className="flex gap-3 pt-4">
                <button type="button" onClick={() => setShowGlobalModal(false)} className="flex-1 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg">Cancel</button>
                <button type="submit" disabled={processing} className="flex-1 py-2 bg-pink-500 hover:bg-pink-600 disabled:opacity-50 text-white rounded-lg flex items-center justify-center gap-2">
                  {processing && <RefreshCw className="w-4 h-4 animate-spin" />}
                  {processing ? 'Saving...' : 'Save Campaign'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Client Override Modal */}
      {showClientModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-lg mx-4">
            <div className="px-6 py-4 border-b border-gray-800">
              <h3 className="text-lg font-bold text-white">{editingOverride ? 'Edit Client Override' : 'Add Client Override'}</h3>
            </div>
            <form onSubmit={handleSaveClientOverride} className="p-6 space-y-4">
              {!editingOverride && (
                <div>
                  <label className="block text-gray-400 text-sm mb-2">Search Client</label>
                  <input type="text" value={clientSearch} onChange={(e) => { setClientSearch(e.target.value); searchClients(e.target.value); }} className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white" placeholder="Search by username..." />
                  {clientSearchResults.length > 0 && (
                    <div className="mt-2 bg-gray-800 border border-gray-700 rounded-lg overflow-hidden">
                      {clientSearchResults.map((c) => (
                        <button key={c.user_id} type="button" onClick={() => { setClientForm(f => ({ ...f, user_id: c.user_id, username: c.username })); setClientSearchResults([]); setClientSearch(''); }} className="w-full px-4 py-2 text-left text-white hover:bg-gray-700 flex items-center gap-2">
                          <User className="w-4 h-4 text-gray-500" />
                          {c.display_name || c.username} <span className="text-gray-500">@{c.username}</span>
                        </button>
                      ))}
                    </div>
                  )}
                  {clientForm.user_id && (
                    <div className="mt-2 p-2 bg-emerald-500/20 border border-emerald-500/30 rounded-lg text-emerald-400 text-sm">
                      Selected: @{clientForm.username}
                    </div>
                  )}
                </div>
              )}
              {editingOverride && (
                <div className="p-3 bg-gray-800 rounded-lg">
                  <p className="text-gray-400 text-sm">Client</p>
                  <p className="text-white font-semibold">@{clientForm.username}</p>
                </div>
              )}
              <div>
                <label className="block text-gray-400 text-sm mb-2">Bonus Percentage</label>
                <div className="flex items-center gap-2">
                  <input type="number" required value={clientForm.bonus_percentage} onChange={(e) => setClientForm(f => ({ ...f, bonus_percentage: parseFloat(e.target.value) || 0 }))} className="w-24 px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-center" min="0" max="100" />
                  <span className="text-gray-400">%</span>
                </div>
              </div>
              <div>
                <label className="block text-gray-400 text-sm mb-2">Expires At (Optional)</label>
                <input type="datetime-local" value={clientForm.expires_at} onChange={(e) => setClientForm(f => ({ ...f, expires_at: e.target.value }))} className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white" />
              </div>
              <div>
                <label className="block text-gray-400 text-sm mb-2">Reason</label>
                <textarea required value={clientForm.reason} onChange={(e) => setClientForm(f => ({ ...f, reason: e.target.value }))} className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white" rows={2} placeholder="VIP client, special arrangement..." />
              </div>
              <div className="flex gap-3 pt-4">
                <button type="button" onClick={() => setShowClientModal(false)} className="flex-1 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg">Cancel</button>
                <button type="submit" disabled={processing || (!editingOverride && !clientForm.user_id)} className="flex-1 py-2 bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 text-white rounded-lg flex items-center justify-center gap-2">
                  {processing && <RefreshCw className="w-4 h-4 animate-spin" />}
                  {processing ? 'Saving...' : 'Save Override'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminReferrals;

/**
 * Admin Rules Engine Page
 * Global defaults for the platform
 * Uses centralized admin API client
 */
import React, { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Switch } from '../../components/ui/switch';
import { 
  Scale, 
  DollarSign, 
  Percent, 
  Save,
  RefreshCw,
  Info,
  AlertTriangle,
  AlertCircle
} from 'lucide-react';

// Centralized Admin API
import { rulesApi, getErrorMessage } from '../../api/admin';

const AdminRules = () => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [rules, setRules] = useState({
    signup_bonus: 0,
    default_deposit_bonus: 0,
    default_referral_bonus: 5,
    deposit_block_balance: 5,
    min_cashout_multiplier: 1,
    max_cashout_multiplier: 3,
    auto_approve_deposits: false,
    auto_approve_withdrawals: false
  });

  const fetchRules = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await rulesApi.getRules();
      const data = response.data;
      setRules({
        signup_bonus: data.global_defaults?.signup_bonus_percent || 0,
        default_deposit_bonus: data.global_defaults?.default_deposit_bonus_percent || 0,
        default_referral_bonus: data.global_defaults?.default_referral_bonus_percent || 5,
        deposit_block_balance: data.global_defaults?.deposit_block_balance || 5,
        min_cashout_multiplier: data.global_defaults?.min_cashout_multiplier || 1,
        max_cashout_multiplier: data.global_defaults?.max_cashout_multiplier || 3,
        auto_approve_deposits: data.approval_defaults?.auto_approve_deposits || false,
        auto_approve_withdrawals: data.approval_defaults?.auto_approve_withdrawals || false
      });
    } catch (err) {
      console.error('Failed to fetch rules:', err);
      setError(getErrorMessage(err, 'Failed to load rules'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRules();
  }, [fetchRules]);

  const saveRules = async () => {
    setSaving(true);
    try {
      await rulesApi.updateRules(rules);
      toast.success('Global rules saved successfully');
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to save rules'));
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-emerald-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-3" />
          <p className="text-red-400 mb-4">{error}</p>
          <Button onClick={fetchRules}>Try Again</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="rules-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Scale className="w-6 h-6 text-emerald-400" />
            Rules
          </h1>
          <p className="text-gray-400 text-sm">Global defaults for the platform</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={fetchRules} variant="outline" size="sm" data-testid="reset-rules-btn">
            <RefreshCw className="w-4 h-4 mr-2" />
            Reset
          </Button>
          <Button onClick={saveRules} disabled={saving} size="sm" data-testid="save-rules-btn">
            <Save className="w-4 h-4 mr-2" />
            {saving ? 'Saving...' : 'Save Rules'}
          </Button>
        </div>
      </div>

      {/* Info Banner */}
      <Card className="bg-blue-500/10 border-blue-500/30">
        <CardContent className="py-4">
          <div className="flex items-start gap-3">
            <Info className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-blue-300">
              <p className="font-medium">This page manages GLOBAL DEFAULTS only</p>
              <p className="text-blue-400/80 mt-1">
                Per-client overrides are managed in <span className="font-medium">Clients</span>. 
                Per-game settings are managed in <span className="font-medium">Games</span>.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Bonus Defaults */}
        <Card className="bg-gray-900 border-gray-800">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-emerald-400">
              <Percent className="w-5 h-5" />
              Bonus Defaults
            </CardTitle>
            <CardDescription>Default bonus percentages for new users</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="signup_bonus">Signup Bonus (%)</Label>
              <Input
                id="signup_bonus"
                type="number"
                min="0"
                max="100"
                value={rules.signup_bonus}
                onChange={(e) => setRules({...rules, signup_bonus: parseFloat(e.target.value) || 0})}
                className="bg-gray-800 border-gray-700"
                data-testid="signup-bonus-input"
              />
              <p className="text-xs text-gray-500">Applied on FIRST-EVER deposit (any game)</p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="default_deposit_bonus">Default Deposit Bonus (%)</Label>
              <Input
                id="default_deposit_bonus"
                type="number"
                min="0"
                max="100"
                value={rules.default_deposit_bonus}
                onChange={(e) => setRules({...rules, default_deposit_bonus: parseFloat(e.target.value) || 0})}
                className="bg-gray-800 border-gray-700"
                data-testid="deposit-bonus-input"
              />
              <p className="text-xs text-gray-500">Used when no game or client override exists</p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="default_referral_bonus">Default Referral Bonus (%)</Label>
              <Input
                id="default_referral_bonus"
                type="number"
                min="0"
                max="100"
                value={rules.default_referral_bonus}
                onChange={(e) => setRules({...rules, default_referral_bonus: parseFloat(e.target.value) || 0})}
                className="bg-gray-800 border-gray-700"
                data-testid="referral-bonus-input"
              />
              <p className="text-xs text-gray-500">Applied when using a referral code</p>
            </div>
          </CardContent>
        </Card>

        {/* Cashout Rules */}
        <Card className="bg-gray-900 border-gray-800">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-blue-400">
              <DollarSign className="w-5 h-5" />
              Cashout Rules
            </CardTitle>
            <CardDescription>Min/Max based on last deposit multiplier</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="min_cashout_multiplier">Min Cashout Multiplier (×)</Label>
              <Input
                id="min_cashout_multiplier"
                type="number"
                min="0.1"
                step="0.1"
                value={rules.min_cashout_multiplier}
                onChange={(e) => setRules({...rules, min_cashout_multiplier: parseFloat(e.target.value) || 1})}
                className="bg-gray-800 border-gray-700"
                data-testid="min-multiplier-input"
              />
              <p className="text-xs text-gray-500">Min withdrawal = X × last deposit</p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="max_cashout_multiplier">Max Cashout Multiplier (×)</Label>
              <Input
                id="max_cashout_multiplier"
                type="number"
                min="0.1"
                step="0.1"
                value={rules.max_cashout_multiplier}
                onChange={(e) => setRules({...rules, max_cashout_multiplier: parseFloat(e.target.value) || 3})}
                className="bg-gray-800 border-gray-700"
                data-testid="max-multiplier-input"
              />
              <p className="text-xs text-gray-500">Max withdrawal = Y × last deposit (excess is voided)</p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="deposit_block_balance">Deposit Block Balance ($)</Label>
              <Input
                id="deposit_block_balance"
                type="number"
                min="0"
                value={rules.deposit_block_balance}
                onChange={(e) => setRules({...rules, deposit_block_balance: parseFloat(e.target.value) || 5})}
                className="bg-gray-800 border-gray-700"
                data-testid="deposit-block-input"
              />
              <p className="text-xs text-gray-500">Block deposits if balance exceeds this amount</p>
            </div>
          </CardContent>
        </Card>

        {/* Approval Defaults */}
        <Card className="bg-gray-900 border-gray-800 md:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-purple-400">
              <AlertTriangle className="w-5 h-5" />
              Approval Defaults
            </CardTitle>
            <CardDescription>Auto-approval settings (use with caution)</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="flex items-center justify-between p-4 bg-gray-800 rounded-lg">
                <div>
                  <Label>Auto-Approve Deposits</Label>
                  <p className="text-xs text-gray-500 mt-1">Skip manual review for deposits</p>
                </div>
                <Switch
                  checked={rules.auto_approve_deposits}
                  onCheckedChange={(v) => setRules({...rules, auto_approve_deposits: v})}
                  data-testid="auto-approve-deposits"
                />
              </div>

              <div className="flex items-center justify-between p-4 bg-gray-800 rounded-lg">
                <div>
                  <Label>Auto-Approve Withdrawals</Label>
                  <p className="text-xs text-gray-500 mt-1">Skip manual review for withdrawals</p>
                </div>
                <Switch
                  checked={rules.auto_approve_withdrawals}
                  onCheckedChange={(v) => setRules({...rules, auto_approve_withdrawals: v})}
                  data-testid="auto-approve-withdrawals"
                />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Consumption Order Info */}
      <Card className="bg-gray-900/50 border-gray-800">
        <CardContent className="py-4">
          <p className="text-sm text-gray-400">
            <span className="text-white font-medium">Balance Consumption Order:</span>{' '}
            CASH → PLAY CREDITS → BONUS
          </p>
          <p className="text-xs text-gray-500 mt-1">
            Bonus does NOT increase cashout multiplier base. Bonus IS withdrawable if multiplier condition is met.
          </p>
        </CardContent>
      </Card>
    </div>
  );
};

export default AdminRules;

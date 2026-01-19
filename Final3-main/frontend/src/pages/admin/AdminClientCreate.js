import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { ArrowLeft, Save, Key, Gift, AlertTriangle, RefreshCw } from 'lucide-react';

// Centralized Admin API
import { usersApi, getErrorMessage } from '../../api/admin';

const AdminClientCreate = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [generatedPassword, setGeneratedPassword] = useState(null);
  const [form, setForm] = useState({
    username: '',
    password: '',
    display_name: '',
    initial_bonus: 0,
    manual_approval_required: false,
    bonus_disabled: false,
    withdraw_disabled: false
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!form.username) {
      toast.error('Username is required');
      return;
    }

    setLoading(true);
    try {
      const response = await usersApi.create(form);
      const data = response.data;
      
      // Use generated_password (preferred) or fallback to password (backward compat)
      const receivedPassword = data.generated_password || data.password;
      if (receivedPassword) {
        setGeneratedPassword(receivedPassword);
        toast.success('Client created successfully');
        
        // Auto-navigate after delay
        setTimeout(() => {
          navigate(`/admin/clients`);
        }, 5000);
      } else {
        // Manual password was used, no password shown
        toast.success('Client created successfully with provided password');
        navigate(`/admin/clients`);
      }
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to create client'));
    } finally {
      setLoading(false);
    }
  };

  if (generatedPassword) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/admin/clients')}
            className="p-2 hover:bg-gray-800 rounded-lg transition"
          >
            <ArrowLeft className="w-5 h-5 text-gray-400" />
          </button>
          <h1 className="text-2xl font-bold text-white">Client Created Successfully</h1>
        </div>

        <Card className="bg-gradient-to-br from-emerald-900/20 to-emerald-900/10 border-emerald-500/30">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-emerald-400">
              <Key className="w-5 h-5" />
              Save Client Credentials - SHOWN ONCE ONLY
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
              <p className="text-red-400 text-sm font-bold mb-2">🔒 CRITICAL SECURITY WARNING</p>
              <p className="text-red-300/70 text-xs">
                This password is shown ONCE and will NEVER be displayed again. Copy it now and store it securely. The server does not store plaintext passwords.
              </p>
            </div>

            <div>
              <label className="block text-gray-400 text-sm mb-1">Username</label>
              <div className="bg-black p-3 rounded-lg font-mono text-white">
                {form.username}
              </div>
            </div>

            <div>
              <label className="block text-gray-400 text-sm mb-1">Generated Password</label>
              <div className="flex gap-2">
                <div className="flex-1 bg-black p-3 rounded-lg font-mono text-emerald-400 break-all">
                  {generatedPassword}
                </div>
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(generatedPassword);
                    toast.success('Password copied to clipboard');
                  }}
                  className="px-4 bg-emerald-500 hover:bg-emerald-600 rounded-lg text-white transition"
                  data-testid="copy-password-btn"
                >
                  Copy
                </button>
              </div>
            </div>

            <p className="text-gray-500 text-sm">
              Redirecting to clients list in 5 seconds...
            </p>

            <Button
              onClick={() => navigate('/admin/clients')}
              className="w-full bg-emerald-500 hover:bg-emerald-600"
            >
              Go to Clients List
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate('/admin/clients')}
          className="p-2 hover:bg-gray-800 rounded-lg transition"
        >
          <ArrowLeft className="w-5 h-5 text-gray-400" />
        </button>
        <h1 className="text-2xl font-bold text-white">Create New Client</h1>
      </div>

      <form onSubmit={handleSubmit}>
        <Card className="bg-gray-900 border-gray-800">
          <CardHeader>
            <CardTitle>Client Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Basic Info */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-gray-400 text-sm mb-1.5">
                  Username <span className="text-red-400">*</span>
                </label>
                <Input
                  type="text"
                  placeholder="client123"
                  value={form.username}
                  onChange={(e) => setForm({...form, username: e.target.value})}
                  className="bg-black border-gray-700"
                  required
                />
              </div>

              <div>
                <label className="block text-gray-400 text-sm mb-1.5">
                  Display Name
                </label>
                <Input
                  type="text"
                  placeholder="Client Name (optional)"
                  value={form.display_name}
                  onChange={(e) => setForm({...form, display_name: e.target.value})}
                  className="bg-black border-gray-700"
                />
              </div>
            </div>

            <div>
              <label className="block text-gray-400 text-sm mb-1.5">
                Password (leave empty to auto-generate)
              </label>
              <Input
                type="password"
                placeholder="Auto-generated if empty"
                value={form.password}
                onChange={(e) => setForm({...form, password: e.target.value})}
                className="bg-black border-gray-700"
              />
              <p className="text-gray-600 text-xs mt-1">
                If empty, a secure password will be generated
              </p>
            </div>

            <div>
              <label className="block text-gray-400 text-sm mb-1.5 flex items-center gap-2">
                <Gift className="w-4 h-4 text-purple-400" />
                Initial Credit Grant (Admin Override)
              </label>
              <Input
                type="number"
                placeholder="0"
                value={form.initial_bonus}
                onChange={(e) => setForm({...form, initial_bonus: parseFloat(e.target.value) || 0})}
                className="bg-black border-gray-700"
                step="0.01"
              />
              <p className="text-gray-600 text-xs mt-1">
                ⚠️ This is a manual admin credit grant, NOT the signup bonus rule. Signup bonus % is configured in Rules → Global Settings.
              </p>
            </div>

            {/* Risk Flags */}
            <div className="pt-3 border-t border-gray-800">
              <p className="text-gray-400 text-sm font-medium mb-3 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-yellow-400" />
                Risk Flags
              </p>
              <div className="space-y-2">
                <label className="flex items-center justify-between p-3 bg-black border border-gray-700 rounded-lg cursor-pointer hover:border-gray-600 transition">
                  <div>
                    <p className="text-white text-sm">Manual Approval Required</p>
                    <p className="text-gray-500 text-xs">All transactions require admin approval</p>
                  </div>
                  <input
                    type="checkbox"
                    checked={form.manual_approval_required}
                    onChange={(e) => setForm({...form, manual_approval_required: e.target.checked})}
                    className="w-5 h-5 rounded border-gray-600 bg-gray-800 text-emerald-500"
                  />
                </label>

                <label className="flex items-center justify-between p-3 bg-black border border-gray-700 rounded-lg cursor-pointer hover:border-gray-600 transition">
                  <div>
                    <p className="text-white text-sm">Bonus Disabled</p>
                    <p className="text-gray-500 text-xs">No bonuses awarded on deposits</p>
                  </div>
                  <input
                    type="checkbox"
                    checked={form.bonus_disabled}
                    onChange={(e) => setForm({...form, bonus_disabled: e.target.checked})}
                    className="w-5 h-5 rounded border-gray-600 bg-gray-800 text-red-500"
                  />
                </label>

                <label className="flex items-center justify-between p-3 bg-black border border-gray-700 rounded-lg cursor-pointer hover:border-gray-600 transition">
                  <div>
                    <p className="text-white text-sm">Withdraw Disabled</p>
                    <p className="text-gray-500 text-xs">Client cannot initiate withdrawals</p>
                  </div>
                  <input
                    type="checkbox"
                    checked={form.withdraw_disabled}
                    onChange={(e) => setForm({...form, withdraw_disabled: e.target.checked})}
                    className="w-5 h-5 rounded border-gray-600 bg-gray-800 text-orange-500"
                  />
                </label>
              </div>
            </div>

            <div className="flex gap-3 pt-4">
              <Button
                type="button"
                onClick={() => navigate('/admin/clients')}
                variant="outline"
                className="flex-1"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={loading}
                className="flex-1 bg-emerald-500 hover:bg-emerald-600"
              >
                <Save className="w-4 h-4 mr-2" />
                {loading ? 'Creating...' : 'Create Client'}
              </Button>
            </div>
          </CardContent>
        </Card>
      </form>
    </div>
  );
};

export default AdminClientCreate;

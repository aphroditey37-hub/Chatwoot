/**
 * System API Access Page
 * Manage API keys for external integrations
 * Uses centralized admin API client
 */
import React, { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/card';
import { Button } from '../../../components/ui/button';
import { Input } from '../../../components/ui/input';
import { Key, Plus, Trash2, Copy, Eye, EyeOff, RefreshCw, CheckCircle, AlertCircle, X } from 'lucide-react';

// Centralized Admin API
import { apiKeysApi, getErrorMessage } from '../../../api/admin';

const SystemAPIAccess = () => {
  const [apiKeys, setApiKeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [newKey, setNewKey] = useState(null);
  const [visibleKeys, setVisibleKeys] = useState({});
  const [copied, setCopied] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({
    name: '',
    scopes: []
  });

  const availableScopes = [
    { value: 'read:orders', label: 'Read Orders' },
    { value: 'write:orders', label: 'Write Orders' },
    { value: 'read:users', label: 'Read Users' },
    { value: 'write:users', label: 'Write Users' },
    { value: 'read:games', label: 'Read Games' },
    { value: 'write:games', label: 'Write Games' },
    { value: 'admin:all', label: 'Full Admin Access' }
  ];

  const fetchAPIKeys = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiKeysApi.getAll();
      setApiKeys(response.data.api_keys || []);
    } catch (err) {
      console.error('Failed to fetch API keys:', err);
      if (err.response?.status === 404) {
        setApiKeys([]);
        setError(null);
      } else {
        setError(getErrorMessage(err, 'Could not load API keys'));
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAPIKeys();
  }, [fetchAPIKeys]);

  const handleCreate = async () => {
    if (!form.name || form.scopes.length === 0) {
      toast.error('Please provide a name and select at least one scope');
      return;
    }

    setSubmitting(true);
    try {
      const response = await apiKeysApi.create(form);
      setNewKey(response.data.api_key);
      setForm({ name: '', scopes: [] });
      fetchAPIKeys();
      toast.success('API key created');
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to create API key'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleRevoke = async (id) => {
    if (!window.confirm('Revoke this API key? This action cannot be undone.')) return;

    try {
      await apiKeysApi.revoke(id);
      toast.success('API key revoked');
      fetchAPIKeys();
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to revoke API key'));
    }
  };

  const handleScopeToggle = (scope) => {
    if (form.scopes.includes(scope)) {
      setForm({ ...form, scopes: form.scopes.filter(s => s !== scope) });
    } else {
      setForm({ ...form, scopes: [...form.scopes, scope] });
    }
  };

  const toggleVisibility = (id) => {
    setVisibleKeys({ ...visibleKeys, [id]: !visibleKeys[id] });
  };

  const copyToClipboard = (key, id) => {
    navigator.clipboard.writeText(key);
    setCopied({ ...copied, [id]: true });
    toast.success('Copied to clipboard');
    setTimeout(() => setCopied({ ...copied, [id]: false }), 2000);
  };

  const maskKey = (key) => {
    if (!key || key.length < 16) return key || '';
    return key.substring(0, 8) + '•'.repeat(32) + key.substring(key.length - 8);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-emerald-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="api-access-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Key className="w-6 h-6 text-blue-400" />
            API Access
          </h1>
          <p className="text-gray-400 text-sm mt-1">Manage API keys for external integrations</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={fetchAPIKeys} variant="outline" size="icon" data-testid="refresh-keys-btn">
            <RefreshCw className="w-4 h-4" />
          </Button>
          <Button onClick={() => setShowModal(true)} className="bg-emerald-500 hover:bg-emerald-600" data-testid="generate-key-btn">
            <Plus className="w-4 h-4 mr-2" />
            Generate Key
          </Button>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-yellow-400 font-medium">Notice</p>
            <p className="text-yellow-300/70 text-sm">{error}</p>
          </div>
        </div>
      )}

      {/* API Keys List */}
      <div className="space-y-3">
        {apiKeys.length === 0 ? (
          <Card className="bg-gray-900 border-gray-800">
            <CardContent className="py-12 text-center">
              <Key className="w-12 h-12 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-500">No API keys generated</p>
              <p className="text-gray-600 text-sm mt-1">Create an API key to integrate with external services</p>
            </CardContent>
          </Card>
        ) : (
          apiKeys.map(key => (
            <Card key={key.id} className="bg-gray-900 border-gray-800" data-testid={`api-key-${key.id}`}>
              <CardContent className="pt-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-white font-semibold">{key.name}</h3>
                      <span className="px-2 py-1 bg-emerald-500/10 text-emerald-400 text-xs rounded-full flex items-center gap-1">
                        <CheckCircle className="w-3 h-3" />
                        Active
                      </span>
                    </div>
                    <div className="flex items-center gap-2 mb-3">
                      <code className="text-gray-400 text-sm font-mono bg-gray-950 px-3 py-1.5 rounded flex-1">
                        {visibleKeys[key.id] ? key.key : maskKey(key.key)}
                      </code>
                      <button
                        onClick={() => toggleVisibility(key.id)}
                        className="p-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition"
                      >
                        {visibleKeys[key.id] ? <EyeOff className="w-4 h-4 text-gray-400" /> : <Eye className="w-4 h-4 text-gray-400" />}
                      </button>
                      <button
                        onClick={() => copyToClipboard(key.key, key.id)}
                        className="p-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition"
                      >
                        {copied[key.id] ? <CheckCircle className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4 text-gray-400" />}
                      </button>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {key.scopes?.map(scope => (
                        <span key={scope} className="px-2 py-1 bg-gray-800 text-gray-300 text-xs rounded">
                          {scope}
                        </span>
                      ))}
                    </div>
                    <p className="text-gray-500 text-xs mt-2">
                      Created {key.created_at ? new Date(key.created_at).toLocaleDateString() : 'N/A'}
                    </p>
                  </div>
                  <button
                    onClick={() => handleRevoke(key.id)}
                    className="p-2 bg-red-500/10 text-red-400 hover:bg-red-500/20 rounded-lg transition ml-4"
                    data-testid={`revoke-key-${key.id}`}
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {/* Create Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4" onClick={() => !newKey && setShowModal(false)}>
          <Card className="bg-gray-900 border-gray-800 w-full max-w-lg" onClick={e => e.stopPropagation()}>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>{newKey ? 'API Key Created' : 'Generate API Key'}</CardTitle>
              <button onClick={() => { setShowModal(false); setNewKey(null); }} className="text-gray-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </CardHeader>
            <CardContent className="space-y-4">
              {newKey ? (
                <>
                  <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4">
                    <p className="text-yellow-400 text-sm font-medium mb-2">⚠️ Save this key now!</p>
                    <p className="text-yellow-300/70 text-xs">You won't be able to see it again.</p>
                  </div>
                  <div>
                    <label className="block text-gray-400 text-sm mb-1">Your API Key</label>
                    <div className="flex gap-2">
                      <code className="flex-1 bg-gray-950 text-emerald-400 p-3 rounded font-mono text-sm break-all">
                        {newKey}
                      </code>
                      <button
                        onClick={() => copyToClipboard(newKey, 'new')}
                        className="p-3 bg-emerald-500 hover:bg-emerald-600 rounded transition"
                      >
                        {copied['new'] ? <CheckCircle className="w-5 h-5 text-white" /> : <Copy className="w-5 h-5 text-white" />}
                      </button>
                    </div>
                  </div>
                  <Button 
                    onClick={() => {
                      setShowModal(false);
                      setNewKey(null);
                    }} 
                    className="w-full bg-emerald-500 hover:bg-emerald-600"
                  >
                    Done
                  </Button>
                </>
              ) : (
                <>
                  <div>
                    <label className="block text-gray-400 text-sm mb-1">Key Name</label>
                    <Input
                      placeholder="Production API"
                      value={form.name}
                      onChange={(e) => setForm({ ...form, name: e.target.value })}
                      className="bg-gray-800 border-gray-700"
                      data-testid="key-name-input"
                    />
                  </div>
                  <div>
                    <label className="block text-gray-400 text-sm mb-2">Permissions</label>
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                      {availableScopes.map(scope => (
                        <label key={scope.value} className="flex items-center gap-2 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={form.scopes.includes(scope.value)}
                            onChange={() => handleScopeToggle(scope.value)}
                            className="w-4 h-4 rounded border-gray-600 bg-gray-800 text-emerald-500"
                          />
                          <span className="text-gray-300 text-sm">{scope.label}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                  <div className="flex gap-2 pt-4">
                    <Button onClick={() => setShowModal(false)} variant="outline" className="flex-1">
                      Cancel
                    </Button>
                    <Button 
                      onClick={handleCreate} 
                      disabled={submitting}
                      className="flex-1 bg-emerald-500 hover:bg-emerald-600"
                      data-testid="create-key-btn"
                    >
                      {submitting ? <RefreshCw className="w-4 h-4 animate-spin" /> : 'Generate Key'}
                    </Button>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
};

export default SystemAPIAccess;

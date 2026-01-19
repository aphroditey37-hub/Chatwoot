/**
 * System Webhooks Management Page
 * Configure webhook endpoints and view delivery history
 * Uses centralized admin API client
 */
import React, { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/card';
import { Button } from '../../../components/ui/button';
import { Input } from '../../../components/ui/input';
import { Webhook, Plus, Trash2, Power, RefreshCw, CheckCircle, XCircle, AlertCircle, History, X } from 'lucide-react';

// Centralized Admin API
import { systemApi, getErrorMessage } from '../../../api/admin';

const SystemWebhooks = () => {
  const [webhooks, setWebhooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [showDeliveries, setShowDeliveries] = useState(null);
  const [deliveries, setDeliveries] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({
    name: '',
    url: '',
    events: [],
    enabled: true
  });

  const availableEvents = [
    { value: 'deposit.approved', label: 'Deposit Approved' },
    { value: 'deposit.rejected', label: 'Deposit Rejected' },
    { value: 'withdrawal.approved', label: 'Withdrawal Approved' },
    { value: 'withdrawal.rejected', label: 'Withdrawal Rejected' },
    { value: 'user.registered', label: 'User Registered' },
    { value: 'promo.redeemed', label: 'Promo Code Redeemed' },
    { value: 'referral.earned', label: 'Referral Commission Earned' }
  ];

  const fetchWebhooks = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await systemApi.getWebhooks();
      setWebhooks(response.data.webhooks || []);
    } catch (err) {
      console.error('Failed to fetch webhooks:', err);
      if (err.response?.status === 404) {
        setWebhooks([]);
        setError(null);
      } else {
        setError(getErrorMessage(err, 'Could not load webhooks'));
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchWebhooks();
  }, [fetchWebhooks]);

  const handleCreate = async () => {
    if (!form.name || !form.url) {
      toast.error('Name and URL are required');
      return;
    }

    setSubmitting(true);
    try {
      await systemApi.createWebhook(form);
      toast.success('Webhook created successfully');
      setShowModal(false);
      setForm({ name: '', url: '', events: [], enabled: true });
      fetchWebhooks();
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to create webhook'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleToggle = async (webhookId, currentEnabled) => {
    try {
      await systemApi.updateWebhook(webhookId, { enabled: !currentEnabled });
      toast.success(currentEnabled ? 'Webhook disabled' : 'Webhook enabled');
      fetchWebhooks();
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to update webhook'));
    }
  };

  const handleDelete = async (webhookId) => {
    if (!window.confirm('Are you sure you want to delete this webhook?')) return;

    try {
      await systemApi.deleteWebhook(webhookId);
      toast.success('Webhook deleted');
      fetchWebhooks();
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to delete webhook'));
    }
  };

  const loadDeliveries = async (webhookId) => {
    try {
      const response = await systemApi.getWebhookDeliveries(webhookId, 50);
      setDeliveries(response.data.deliveries || []);
      setShowDeliveries(webhookId);
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to load deliveries'));
    }
  };

  const toggleEvent = (eventValue) => {
    if (form.events.includes(eventValue)) {
      setForm({ ...form, events: form.events.filter(e => e !== eventValue) });
    } else {
      setForm({ ...form, events: [...form.events, eventValue] });
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-violet-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="system-webhooks-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Webhook className="w-6 h-6 text-violet-400" />
            Webhooks
          </h1>
          <p className="text-gray-400 text-sm">Receive real-time notifications via HTTP callbacks</p>
        </div>
        <div className="flex gap-2">
          <Button
            onClick={fetchWebhooks}
            variant="outline"
            size="icon"
            data-testid="refresh-webhooks-btn"
          >
            <RefreshCw className="w-4 h-4" />
          </Button>
          <Button
            onClick={() => setShowModal(true)}
            className="bg-violet-600 hover:bg-violet-700"
            data-testid="add-webhook-btn"
          >
            <Plus className="w-4 h-4 mr-2" />
            Add Webhook
          </Button>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-red-400" />
          <p className="text-red-400">{error}</p>
          <Button onClick={fetchWebhooks} variant="ghost" size="sm" className="ml-auto">
            Retry
          </Button>
        </div>
      )}

      {/* Webhooks List */}
      <Card className="bg-gray-900 border-gray-800">
        <CardHeader>
          <CardTitle className="text-lg text-white">Configured Webhooks</CardTitle>
        </CardHeader>
        <CardContent>
          {webhooks.length === 0 ? (
            <div className="py-12 text-center">
              <Webhook className="w-12 h-12 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-400">No webhooks configured</p>
              <p className="text-gray-600 text-sm">Create a webhook to receive event notifications</p>
            </div>
          ) : (
            <div className="space-y-3">
              {webhooks.map(webhook => (
                <div 
                  key={webhook.webhook_id} 
                  className={`p-4 rounded-lg border ${
                    webhook.enabled 
                      ? 'bg-gray-800 border-gray-700' 
                      : 'bg-gray-800/50 border-gray-800 opacity-60'
                  }`}
                  data-testid={`webhook-${webhook.webhook_id}`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="text-white font-medium">{webhook.name}</h3>
                        {webhook.enabled ? (
                          <CheckCircle className="w-4 h-4 text-emerald-400" />
                        ) : (
                          <XCircle className="w-4 h-4 text-gray-500" />
                        )}
                      </div>
                      <p className="text-gray-500 text-sm font-mono break-all">{webhook.url}</p>
                      <div className="flex flex-wrap gap-1 mt-2">
                        {(webhook.events || []).map(event => (
                          <span key={event} className="px-2 py-0.5 bg-violet-500/20 text-violet-400 text-xs rounded">
                            {event}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => loadDeliveries(webhook.webhook_id)}
                        title="View deliveries"
                        data-testid={`deliveries-${webhook.webhook_id}`}
                      >
                        <History className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleToggle(webhook.webhook_id, webhook.enabled)}
                        title={webhook.enabled ? 'Disable' : 'Enable'}
                        data-testid={`toggle-${webhook.webhook_id}`}
                      >
                        <Power className={`w-4 h-4 ${webhook.enabled ? 'text-emerald-400' : 'text-gray-500'}`} />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(webhook.webhook_id)}
                        className="text-red-400 hover:text-red-300"
                        data-testid={`delete-${webhook.webhook_id}`}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4">
          <Card className="bg-gray-900 border-gray-800 w-full max-w-md">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Create Webhook</CardTitle>
              <button onClick={() => setShowModal(false)} className="text-gray-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-gray-400 text-sm mb-1">Name *</label>
                <Input
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="My Webhook"
                  className="bg-black border-gray-700"
                  data-testid="webhook-name-input"
                />
              </div>
              <div>
                <label className="block text-gray-400 text-sm mb-1">URL *</label>
                <Input
                  value={form.url}
                  onChange={(e) => setForm({ ...form, url: e.target.value })}
                  placeholder="https://example.com/webhook"
                  className="bg-black border-gray-700"
                  data-testid="webhook-url-input"
                />
              </div>
              <div>
                <label className="block text-gray-400 text-sm mb-2">Events</label>
                <div className="space-y-2">
                  {availableEvents.map(event => (
                    <label key={event.value} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={form.events.includes(event.value)}
                        onChange={() => toggleEvent(event.value)}
                        className="w-4 h-4 rounded border-gray-600 bg-gray-800 text-violet-500"
                      />
                      <span className="text-gray-300 text-sm">{event.label}</span>
                    </label>
                  ))}
                </div>
              </div>
              <div className="flex gap-2 pt-4">
                <Button
                  variant="outline"
                  onClick={() => setShowModal(false)}
                  className="flex-1"
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleCreate}
                  disabled={submitting}
                  className="flex-1 bg-violet-600 hover:bg-violet-700"
                  data-testid="create-webhook-btn"
                >
                  {submitting ? <RefreshCw className="w-4 h-4 animate-spin" /> : 'Create'}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Deliveries Modal */}
      {showDeliveries && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4">
          <Card className="bg-gray-900 border-gray-800 w-full max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Delivery History</CardTitle>
              <button onClick={() => setShowDeliveries(null)} className="text-gray-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </CardHeader>
            <CardContent className="overflow-auto flex-1">
              {deliveries.length === 0 ? (
                <div className="py-8 text-center text-gray-500">
                  No deliveries recorded yet
                </div>
              ) : (
                <div className="space-y-2">
                  {deliveries.map((d, i) => (
                    <div key={i} className="p-3 bg-gray-800 rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-gray-400 text-sm">{d.event}</span>
                        <span className={`px-2 py-0.5 rounded text-xs ${
                          d.status === 'success' 
                            ? 'bg-emerald-500/20 text-emerald-400' 
                            : 'bg-red-500/20 text-red-400'
                        }`}>
                          {d.status} ({d.status_code})
                        </span>
                      </div>
                      <p className="text-gray-600 text-xs">
                        {d.delivered_at ? new Date(d.delivered_at).toLocaleString() : '-'}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
};

export default SystemWebhooks;

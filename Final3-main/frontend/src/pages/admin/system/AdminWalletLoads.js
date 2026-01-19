/**
 * Admin Wallet Loads Page
 * Monitor wallet load requests (read-only)
 * Uses centralized admin API client
 */
import React, { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import { 
  Wallet, RefreshCw, Clock, Eye, User, 
  CreditCard, AlertCircle, CheckCircle, XCircle, ExternalLink, Bot, X
} from 'lucide-react';

// Centralized Admin API
import { systemApi, getErrorMessage } from '../../../api/admin';

const AdminWalletLoads = () => {
  const [loading, setLoading] = useState(true);
  const [requests, setRequests] = useState([]);
  const [statusFilter, setStatusFilter] = useState('all');
  const [selectedRequest, setSelectedRequest] = useState(null);
  const [error, setError] = useState(null);

  const fetchRequests = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = statusFilter !== 'all' ? { status: statusFilter } : {};
      const response = await systemApi.getWalletLoads(params);
      setRequests(response.data.requests || []);
    } catch (err) {
      console.error('Failed to fetch wallet loads:', err);
      setError(getErrorMessage(err, 'Failed to load wallet requests'));
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    fetchRequests();
  }, [fetchRequests]);

  const getStatusBadge = (status) => {
    const styles = {
      pending: { bg: 'bg-yellow-500/20', text: 'text-yellow-400', icon: Clock },
      approved: { bg: 'bg-emerald-500/20', text: 'text-emerald-400', icon: CheckCircle },
      rejected: { bg: 'bg-red-500/20', text: 'text-red-400', icon: XCircle }
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

  if (loading && requests.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-emerald-500" />
      </div>
    );
  }

  if (error && requests.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-3" />
          <p className="text-red-400 mb-4">{error}</p>
          <button 
            onClick={fetchRequests} 
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-lg text-white"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="admin-wallet-loads">
      {/* Info Banner - Telegram Review */}
      <div className="bg-blue-500/20 border border-blue-500/30 rounded-xl p-4">
        <div className="flex items-center gap-3">
          <Bot className="w-8 h-8 text-blue-400 flex-shrink-0" />
          <div className="flex-1">
            <h3 className="text-blue-400 font-bold">Wallet Load Review via Telegram</h3>
            <p className="text-blue-300/80 text-sm">
              Wallet load approvals are handled via Telegram reviewer bots. This page is read-only for monitoring.
            </p>
          </div>
          <a
            href="/admin/system/telegram-bots"
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition text-sm font-medium"
          >
            <ExternalLink className="w-4 h-4" />
            Manage Bots
          </a>
        </div>
      </div>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <Wallet className="w-7 h-7 text-emerald-400" />
            Wallet Load Requests
          </h1>
          <p className="text-gray-400 text-sm">Monitor client funding requests</p>
        </div>
        <button 
          onClick={fetchRequests} 
          className="p-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition"
          data-testid="refresh-loads-btn"
        >
          <RefreshCw className={`w-5 h-5 text-gray-400 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Status Filters */}
      <div className="flex gap-2">
        {['all', 'pending', 'approved', 'rejected'].map(status => (
          <button
            key={status}
            onClick={() => setStatusFilter(status)}
            className={`px-4 py-2 rounded-lg transition capitalize ${
              statusFilter === status
                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                : 'bg-gray-800 text-gray-400 border border-gray-700'
            }`}
          >
            {status}
          </button>
        ))}
      </div>

      {/* Requests List */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        {requests.length === 0 ? (
          <div className="text-center py-12">
            <Wallet className="w-12 h-12 text-gray-600 mx-auto mb-3" />
            <p className="text-gray-400">No wallet load requests</p>
            <p className="text-gray-500 text-sm">
              {statusFilter !== 'all' ? `No ${statusFilter} requests found` : 'Requests will appear here'}
            </p>
          </div>
        ) : (
          <div className="divide-y divide-gray-800">
            {requests.map(req => (
              <div 
                key={req.request_id || req.id} 
                className="p-4 hover:bg-gray-800/50 transition"
                data-testid={`load-${req.request_id || req.id}`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-emerald-500/20 rounded-xl flex items-center justify-center">
                      <CreditCard className="w-6 h-6 text-emerald-400" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-white font-medium">{req.display_name || req.username}</span>
                        {getStatusBadge(req.status)}
                      </div>
                      <div className="text-gray-400 text-sm">
                        {req.payment_method} • {new Date(req.created_at).toLocaleString()}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <div className="text-emerald-400 font-bold text-lg">₱{req.amount?.toFixed(2)}</div>
                      {req.reference_number && (
                        <div className="text-gray-500 text-xs font-mono">{req.reference_number}</div>
                      )}
                    </div>
                    <button 
                      onClick={() => setSelectedRequest(req)}
                      className="p-2 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg"
                    >
                      <Eye className="w-5 h-5" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Detail Modal */}
      {selectedRequest && (
        <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4">
          <div className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-md">
            <div className="px-6 py-4 border-b border-gray-800 flex items-center justify-between">
              <h3 className="text-lg font-bold text-white">Request Details</h3>
              <button onClick={() => setSelectedRequest(null)} className="text-gray-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div className="bg-gray-800 rounded-lg p-4 space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-400">Client</span>
                  <span className="text-white">{selectedRequest.display_name || selectedRequest.username}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Amount</span>
                  <span className="text-emerald-400 font-bold">₱{selectedRequest.amount?.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Method</span>
                  <span className="text-white">{selectedRequest.payment_method}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Reference</span>
                  <span className="text-white font-mono text-sm">{selectedRequest.reference_number || 'N/A'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Status</span>
                  {getStatusBadge(selectedRequest.status)}
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Submitted</span>
                  <span className="text-gray-300 text-sm">{new Date(selectedRequest.created_at).toLocaleString()}</span>
                </div>
              </div>
              
              {selectedRequest.proof_image_url && (
                <div>
                  <p className="text-gray-400 text-sm mb-2">Proof of Payment</p>
                  <img 
                    src={selectedRequest.proof_image_url} 
                    alt="Payment proof" 
                    className="w-full rounded-lg border border-gray-700"
                  />
                </div>
              )}
              
              <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3">
                <p className="text-blue-400 text-sm">
                  Approvals are handled via Telegram. Configure bots to enable approval workflow.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminWalletLoads;

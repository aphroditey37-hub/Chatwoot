/**
 * Admin Promo Codes Page
 * Manage play credit promo codes with filtering, creation, and actions
 * Uses centralized admin API client
 */
import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { toast } from 'sonner';
import { 
  Gift, Plus, RefreshCw, Ban, Eye, Search, CheckCircle, 
  AlertCircle, X
} from 'lucide-react';

// Centralized Admin API
import { promoCodesApi, getErrorMessage } from '../../api/admin';

const AdminPromoCodes = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [codes, setCodes] = useState([]);
  
  // Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  
  // Create form
  const [showCreate, setShowCreate] = useState(false);
  const [newCode, setNewCode] = useState({ 
    code: '', 
    credit_amount: '', 
    max_redemptions: '',
    description: '',
    expires_in_days: ''
  });
  const [creating, setCreating] = useState(false);
  
  // Confirmation modal
  const [confirmModal, setConfirmModal] = useState({ show: false, action: null, codeId: null, codeName: '' });
  const [actionLoading, setActionLoading] = useState(false);

  const fetchCodes = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const params = {};
      if (statusFilter !== 'all') params.status = statusFilter;
      if (searchTerm) params.search = searchTerm;
      
      const response = await promoCodesApi.getAll(params);
      setCodes(response.data.promo_codes || []);
    } catch (err) {
      console.error('Failed to fetch codes:', err);
      setError(getErrorMessage(err, 'Failed to load promo codes'));
    } finally {
      setLoading(false);
    }
  }, [statusFilter, searchTerm]);

  useEffect(() => {
    fetchCodes();
  }, [fetchCodes]);

  // Helper: compute is_expired from expires_at (backend doesn't return is_expired)
  const isExpired = (code) => {
    return code.expires_at && new Date(code.expires_at) < new Date();
  };

  // Filter codes client-side for search (backend may not support search param)
  const filteredCodes = codes.filter(code => {
    const matchesSearch = !searchTerm || 
      code.code?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      code.description?.toLowerCase().includes(searchTerm.toLowerCase());
    
    const expired = isExpired(code);
    const matchesStatus = statusFilter === 'all' ||
      (statusFilter === 'active' && code.is_active && !expired) ||
      (statusFilter === 'inactive' && !code.is_active) ||
      (statusFilter === 'expired' && expired);
    
    return matchesSearch && matchesStatus;
  });

  const createCode = async () => {
    if (!newCode.code || !newCode.credit_amount) {
      toast.error('Please fill in code and amount');
      return;
    }
    
    const amount = parseFloat(newCode.credit_amount);
    if (amount <= 0 || amount > 10000) {
      toast.error('Amount must be between $1 and $10,000');
      return;
    }
    
    setCreating(true);
    try {
      const payload = {
        code: newCode.code.toUpperCase(),
        credit_amount: amount,
        max_redemptions: newCode.max_redemptions ? parseInt(newCode.max_redemptions) : null,
        description: newCode.description || null
      };
      
      if (newCode.expires_in_days) {
        const expiryDate = new Date();
        expiryDate.setDate(expiryDate.getDate() + parseInt(newCode.expires_in_days));
        payload.expires_at = expiryDate.toISOString();
      }
      
      const response = await promoCodesApi.create(payload);
      
      // Show success with message from API
      toast.success(response.data?.message || 'Promo code created successfully');
      setNewCode({ code: '', credit_amount: '', max_redemptions: '', description: '', expires_in_days: '' });
      setShowCreate(false);
      fetchCodes(); // Refetch list after success
    } catch (err) {
      // Show error with message from API or fallback
      const errorMessage = err.response?.data?.message || getErrorMessage(err, 'Failed to create promo code');
      toast.error(errorMessage);
    } finally {
      setCreating(false);
    }
  };

  const showConfirmation = (action, codeId, codeName) => {
    setConfirmModal({ show: true, action, codeId, codeName });
  };

  const closeConfirmation = () => {
    setConfirmModal({ show: false, action: null, codeId: null, codeName: '' });
  };

  const executeAction = async () => {
    const { action, codeId } = confirmModal;
    setActionLoading(true);
    
    try {
      if (action === 'disable') {
        const response = await promoCodesApi.disable(codeId);
        // Show success with message from API
        toast.success(response.data?.message || 'Promo code disabled');
      }
      fetchCodes(); // Refetch list after success
    } catch (err) {
      // Show error with message from API or fallback
      const errorMessage = err.response?.data?.message || getErrorMessage(err, `Failed to ${action} promo code`);
      toast.error(errorMessage);
    } finally {
      setActionLoading(false);
      closeConfirmation();
    }
  };

  const getStatusBadge = (code) => {
    // Compute expired status from expires_at (backend doesn't return is_expired)
    const expired = code.expires_at && new Date(code.expires_at) < new Date();
    
    if (expired) {
      return <span className="px-2 py-1 rounded text-xs bg-gray-500/10 text-gray-400">Expired</span>;
    }
    if (code.is_active) {
      return <span className="px-2 py-1 rounded text-xs bg-emerald-500/10 text-emerald-400">Active</span>;
    }
    return <span className="px-2 py-1 rounded text-xs bg-red-500/10 text-red-400">Disabled</span>;
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  // Loading State
  if (loading && codes.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-emerald-500" />
      </div>
    );
  }

  // Error State
  if (error && codes.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-3" />
          <p className="text-red-400 mb-4">{error}</p>
          <Button onClick={fetchCodes} variant="outline">Try Again</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="promo-codes-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Gift className="w-6 h-6 text-purple-400" />
            Promo Codes
          </h1>
          <p className="text-gray-400 text-sm">{filteredCodes.length} promo codes</p>
        </div>
        <div className="flex gap-2">
          <button 
            onClick={fetchCodes} 
            disabled={loading}
            className="p-2 hover:bg-gray-800 rounded-lg text-gray-400 hover:text-white transition"
          >
            <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <Button onClick={() => setShowCreate(!showCreate)} size="sm" data-testid="create-promo-btn">
            <Plus className="w-4 h-4 mr-2" />
            Create Code
          </Button>
        </div>
      </div>

      {/* Error Banner */}
      {error && codes.length > 0 && (
        <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={fetchCodes} className="text-red-300 hover:text-white">Retry</button>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <Input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search by code or description..."
            className="pl-10 bg-gray-900 border-gray-700"
            data-testid="search-input"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-emerald-500"
          data-testid="status-filter"
        >
          <option value="all">All Status</option>
          <option value="active">Active</option>
          <option value="inactive">Disabled</option>
          <option value="expired">Expired</option>
        </select>
      </div>

      {/* Create Form */}
      {showCreate && (
        <Card className="bg-gray-900 border-gray-800">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-lg">Create Promo Code</CardTitle>
            <button onClick={() => setShowCreate(false)} className="text-gray-400 hover:text-white">
              <X className="w-5 h-5" />
            </button>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Code *</Label>
                <Input
                  placeholder="SUMMER2024"
                  value={newCode.code}
                  onChange={(e) => setNewCode({...newCode, code: e.target.value.toUpperCase()})}
                  className="bg-gray-800 border-gray-700"
                  maxLength={20}
                  data-testid="code-input"
                />
                <p className="text-xs text-gray-500">Alphanumeric, max 20 characters</p>
              </div>
              <div className="space-y-2">
                <Label>Credit Amount ($) *</Label>
                <Input
                  type="number"
                  placeholder="10"
                  min="1"
                  max="10000"
                  value={newCode.credit_amount}
                  onChange={(e) => setNewCode({...newCode, credit_amount: e.target.value})}
                  className="bg-gray-800 border-gray-700"
                  data-testid="amount-input"
                />
              </div>
              <div className="space-y-2">
                <Label>Max Redemptions</Label>
                <Input
                  type="number"
                  placeholder="Unlimited"
                  min="1"
                  value={newCode.max_redemptions}
                  onChange={(e) => setNewCode({...newCode, max_redemptions: e.target.value})}
                  className="bg-gray-800 border-gray-700"
                  data-testid="max-redemptions-input"
                />
                <p className="text-xs text-gray-500">Leave blank for unlimited</p>
              </div>
              <div className="space-y-2">
                <Label>Expires In (Days)</Label>
                <Input
                  type="number"
                  placeholder="Never expires"
                  min="1"
                  max="365"
                  value={newCode.expires_in_days}
                  onChange={(e) => setNewCode({...newCode, expires_in_days: e.target.value})}
                  className="bg-gray-800 border-gray-700"
                  data-testid="expiry-input"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Description (Optional)</Label>
              <Input
                placeholder="Summer promotion for new users"
                value={newCode.description}
                onChange={(e) => setNewCode({...newCode, description: e.target.value})}
                className="bg-gray-800 border-gray-700"
                maxLength={100}
                data-testid="description-input"
              />
            </div>
            <div className="flex gap-2">
              <Button 
                onClick={createCode} 
                disabled={creating || !newCode.code || !newCode.credit_amount} 
                data-testid="create-code-btn"
              >
                {creating ? (
                  <>
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    Creating...
                  </>
                ) : (
                  'Create Code'
                )}
              </Button>
              <Button variant="outline" onClick={() => setShowCreate(false)}>Cancel</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Codes List */}
      <Card className="bg-gray-900 border-gray-800">
        <CardContent className="pt-4">
          {filteredCodes.length === 0 ? (
            <div className="text-center py-12">
              <Gift className="w-12 h-12 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-500">
                {codes.length === 0 ? 'No promo codes yet' : 'No codes match your filters'}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-800">
                    <th className="text-left text-gray-400 text-xs py-3 px-3">Code</th>
                    <th className="text-left text-gray-400 text-xs py-3 px-3">Description</th>
                    <th className="text-right text-gray-400 text-xs py-3 px-3">Amount</th>
                    <th className="text-center text-gray-400 text-xs py-3 px-3">Usage</th>
                    <th className="text-center text-gray-400 text-xs py-3 px-3">Status</th>
                    <th className="text-center text-gray-400 text-xs py-3 px-3">Expires</th>
                    <th className="text-center text-gray-400 text-xs py-3 px-3">Created</th>
                    <th className="text-right text-gray-400 text-xs py-3 px-3">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredCodes.map((code) => (
                    <tr 
                      key={code.code_id} 
                      className="border-b border-gray-800/50 hover:bg-gray-800/30 transition"
                    >
                      <td className="py-3 px-3">
                        <span className="font-mono text-purple-400 font-medium">{code.code}</span>
                      </td>
                      <td className="py-3 px-3 text-gray-400 text-sm max-w-[200px] truncate">
                        {code.description || '-'}
                      </td>
                      <td className="py-3 px-3 text-right text-emerald-400 font-medium">
                        ${code.credit_amount?.toFixed(2)}
                      </td>
                      <td className="py-3 px-3 text-center text-gray-400">
                        {code.current_redemptions || 0}
                        {code.max_redemptions ? `/${code.max_redemptions}` : ''}
                      </td>
                      <td className="py-3 px-3 text-center">
                        {getStatusBadge(code)}
                      </td>
                      <td className="py-3 px-3 text-center text-gray-500 text-sm">
                        {formatDate(code.expires_at)}
                      </td>
                      <td className="py-3 px-3 text-center text-gray-500 text-sm">
                        {formatDate(code.created_at)}
                      </td>
                      <td className="py-3 px-3 text-right">
                        <div className="flex justify-end gap-1">
                          <button
                            onClick={() => navigate(`/admin/promo-codes/${code.code_id}`)}
                            className="p-1.5 hover:bg-gray-800 rounded text-gray-400 hover:text-white transition"
                            title="View Details"
                            data-testid={`view-${code.code_id}`}
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                          {code.is_active ? (
                            <button
                              onClick={() => showConfirmation('disable', code.code_id, code.code)}
                              className="p-1.5 hover:bg-gray-800 rounded text-gray-400 hover:text-orange-400 transition"
                              title="Disable"
                              data-testid={`disable-${code.code_id}`}
                            >
                              <Ban className="w-4 h-4" />
                            </button>
                          ) : (
                            <span className="p-1.5 text-gray-600" title="Cannot re-enable (one-time disable)">
                              <Ban className="w-4 h-4" />
                            </span>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Confirmation Modal */}
      {confirmModal.show && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <Card className="bg-gray-900 border-gray-800 w-full max-w-md mx-4">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Ban className="w-5 h-5 text-orange-400" />
                Confirm Disable
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-gray-400">
                Are you sure you want to disable promo code{' '}
                <span className="text-purple-400 font-mono">{confirmModal.codeName}</span>?
              </p>
              <p className="text-orange-400/80 text-sm">Note: Disabled codes cannot be re-enabled.</p>
              <div className="flex gap-2 justify-end">
                <Button variant="outline" onClick={closeConfirmation} disabled={actionLoading}>
                  Cancel
                </Button>
                <Button 
                  onClick={executeAction}
                  disabled={actionLoading}
                  className="bg-orange-600 hover:bg-orange-700"
                  data-testid="confirm-action-btn"
                >
                  {actionLoading ? (
                    <RefreshCw className="w-4 h-4 animate-spin" />
                  ) : (
                    'Disable'
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
};

export default AdminPromoCodes;

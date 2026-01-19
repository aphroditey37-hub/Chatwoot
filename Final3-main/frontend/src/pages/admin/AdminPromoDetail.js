/**
 * Admin Promo Code Detail Page
 * View promo code details and redemption history
 * Uses centralized admin API client
 */
import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { toast } from 'sonner';
import { 
  Gift, ArrowLeft, RefreshCw, Ban, AlertCircle, User,
  Calendar, DollarSign, Hash, Clock, CheckCircle, XCircle
} from 'lucide-react';

// Centralized Admin API
import { promoCodesApi, getErrorMessage } from '../../api/admin';

const AdminPromoDetail = () => {
  const { codeId } = useParams();
  const navigate = useNavigate();
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [promoCode, setPromoCode] = useState(null);
  const [redemptions, setRedemptions] = useState([]);
  const [redemptionsLoading, setRedemptionsLoading] = useState(false);
  
  // Confirmation modal
  const [confirmModal, setConfirmModal] = useState({ show: false, action: null });
  const [actionLoading, setActionLoading] = useState(false);

  const fetchPromoCode = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Get all promo codes and find by ID (no getById endpoint exists)
      const allResponse = await promoCodesApi.getAll();
      const found = (allResponse.data.promo_codes || []).find(c => c.code_id === codeId);
      if (found) {
        setPromoCode(found);
      } else {
        throw new Error('Promo code not found');
      }
    } catch (err) {
      console.error('Failed to fetch promo code:', err);
      setError(getErrorMessage(err, 'Failed to load promo code'));
    } finally {
      setLoading(false);
    }
  }, [codeId]);

  const fetchRedemptions = useCallback(async () => {
    setRedemptionsLoading(true);
    try {
      const response = await promoCodesApi.getRedemptions(codeId);
      setRedemptions(response.data.redemptions || []);
    } catch (err) {
      console.error('Failed to fetch redemptions:', err);
      // Don't show error toast, just log it
    } finally {
      setRedemptionsLoading(false);
    }
  }, [codeId]);

  useEffect(() => {
    fetchPromoCode();
    fetchRedemptions();
  }, [fetchPromoCode, fetchRedemptions]);

  const showConfirmation = (action) => {
    setConfirmModal({ show: true, action });
  };

  const closeConfirmation = () => {
    setConfirmModal({ show: false, action: null });
  };

  const executeAction = async () => {
    setActionLoading(true);
    
    try {
      const response = await promoCodesApi.disable(codeId);
      // Show success with message from API
      toast.success(response.data?.message || 'Promo code disabled');
      fetchPromoCode(); // Refetch details after success
    } catch (err) {
      // Show error with message from API or fallback
      const errorMessage = err.response?.data?.message || getErrorMessage(err, 'Failed to disable promo code');
      toast.error(errorMessage);
    } finally {
      setActionLoading(false);
      closeConfirmation();
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getStatusBadge = (code) => {
    // Compute expired status from expires_at (backend doesn't return is_expired)
    const expired = code?.expires_at && new Date(code.expires_at) < new Date();
    
    if (expired) {
      return <span className="px-3 py-1 rounded-full text-sm bg-gray-500/10 text-gray-400">Expired</span>;
    }
    if (code?.is_active) {
      return <span className="px-3 py-1 rounded-full text-sm bg-emerald-500/10 text-emerald-400">Active</span>;
    }
    return <span className="px-3 py-1 rounded-full text-sm bg-red-500/10 text-red-400">Disabled</span>;
  };

  // Loading State
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-emerald-500" />
      </div>
    );
  }

  // Error State
  if (error) {
    return (
      <div className="space-y-4">
        <button
          onClick={() => navigate('/admin/promo-codes')}
          className="flex items-center gap-2 text-gray-400 hover:text-white transition"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Promo Codes
        </button>
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-3" />
            <p className="text-red-400 mb-4">{error}</p>
            <Button onClick={fetchPromoCode} variant="outline">Try Again</Button>
          </div>
        </div>
      </div>
    );
  }

  if (!promoCode) {
    return (
      <div className="space-y-4">
        <button
          onClick={() => navigate('/admin/promo-codes')}
          className="flex items-center gap-2 text-gray-400 hover:text-white transition"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Promo Codes
        </button>
        <div className="text-center py-12">
          <Gift className="w-12 h-12 text-gray-600 mx-auto mb-3" />
          <p className="text-gray-500">Promo code not found</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="promo-detail-page">
      {/* Back Button */}
      <button
        onClick={() => navigate('/admin/promo-codes')}
        className="flex items-center gap-2 text-gray-400 hover:text-white transition"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Promo Codes
      </button>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 bg-purple-500/10 rounded-xl flex items-center justify-center">
            <Gift className="w-6 h-6 text-purple-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white font-mono">{promoCode.code}</h1>
            <p className="text-gray-400 text-sm">{promoCode.description || 'No description'}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {getStatusBadge(promoCode)}
          <Button 
            onClick={fetchPromoCode} 
            variant="outline" 
            size="sm"
          >
            <RefreshCw className="w-4 h-4" />
          </Button>
          {promoCode.is_active && (
            <Button 
              onClick={() => showConfirmation('disable')}
              variant="outline"
              size="sm"
              className="border-orange-500/50 text-orange-400 hover:bg-orange-500/10"
            >
              <Ban className="w-4 h-4 mr-2" />
              Disable
            </Button>
          )}
        </div>
      </div>

      {/* Details Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="bg-gray-900 border-gray-800">
          <CardContent className="pt-5">
            <div className="flex items-center gap-3 mb-2">
              <DollarSign className="w-5 h-5 text-emerald-400" />
              <span className="text-gray-400 text-sm">Credit Amount</span>
            </div>
            <p className="text-2xl font-bold text-emerald-400">
              ${promoCode.credit_amount?.toFixed(2)}
            </p>
          </CardContent>
        </Card>

        <Card className="bg-gray-900 border-gray-800">
          <CardContent className="pt-5">
            <div className="flex items-center gap-3 mb-2">
              <Hash className="w-5 h-5 text-blue-400" />
              <span className="text-gray-400 text-sm">Redemptions</span>
            </div>
            <p className="text-2xl font-bold text-white">
              {promoCode.current_redemptions || 0}
              <span className="text-gray-500 text-lg">
                {promoCode.max_redemptions ? ` / ${promoCode.max_redemptions}` : ' / ∞'}
              </span>
            </p>
          </CardContent>
        </Card>

        <Card className="bg-gray-900 border-gray-800">
          <CardContent className="pt-5">
            <div className="flex items-center gap-3 mb-2">
              <Calendar className="w-5 h-5 text-purple-400" />
              <span className="text-gray-400 text-sm">Created</span>
            </div>
            <p className="text-lg font-medium text-white">
              {formatDate(promoCode.created_at)}
            </p>
          </CardContent>
        </Card>

        <Card className="bg-gray-900 border-gray-800">
          <CardContent className="pt-5">
            <div className="flex items-center gap-3 mb-2">
              <Clock className="w-5 h-5 text-orange-400" />
              <span className="text-gray-400 text-sm">Expires</span>
            </div>
            <p className="text-lg font-medium text-white">
              {promoCode.expires_at ? formatDate(promoCode.expires_at) : 'Never'}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Redemption History */}
      <Card className="bg-gray-900 border-gray-800">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <User className="w-5 h-5 text-gray-400" />
            Redemption History
          </CardTitle>
          <Button 
            onClick={fetchRedemptions} 
            variant="ghost" 
            size="sm"
            disabled={redemptionsLoading}
          >
            <RefreshCw className={`w-4 h-4 ${redemptionsLoading ? 'animate-spin' : ''}`} />
          </Button>
        </CardHeader>
        <CardContent>
          {redemptionsLoading && redemptions.length === 0 ? (
            <div className="flex items-center justify-center py-8">
              <RefreshCw className="w-6 h-6 animate-spin text-gray-500" />
            </div>
          ) : redemptions.length === 0 ? (
            <div className="text-center py-8">
              <User className="w-10 h-10 text-gray-600 mx-auto mb-2" />
              <p className="text-gray-500">No redemptions yet</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-800">
                    <th className="text-left text-gray-400 text-xs py-3 px-3">User</th>
                    <th className="text-right text-gray-400 text-xs py-3 px-3">Amount</th>
                    <th className="text-center text-gray-400 text-xs py-3 px-3">Status</th>
                    <th className="text-right text-gray-400 text-xs py-3 px-3">Date</th>
                  </tr>
                </thead>
                <tbody>
                  {redemptions.map((redemption, index) => (
                    <tr 
                      key={redemption.redemption_id || index} 
                      className="border-b border-gray-800/50"
                    >
                      <td className="py-3 px-3">
                        <div className="flex items-center gap-2">
                          <div className="w-8 h-8 bg-gray-800 rounded-full flex items-center justify-center">
                            <User className="w-4 h-4 text-gray-400" />
                          </div>
                          <div>
                            <p className="text-white font-medium">{redemption.username || 'Unknown'}</p>
                            <p className="text-gray-500 text-xs">{redemption.user_id?.slice(0, 8)}...</p>
                          </div>
                        </div>
                      </td>
                      <td className="py-3 px-3 text-right text-emerald-400 font-medium">
                        +${redemption.credit_amount?.toFixed(2) || promoCode.credit_amount?.toFixed(2)}
                      </td>
                      <td className="py-3 px-3 text-center">
                        {redemption.status === 'failed' ? (
                          <span className="flex items-center justify-center gap-1 text-red-400">
                            <XCircle className="w-4 h-4" />
                            Failed
                          </span>
                        ) : (
                          <span className="flex items-center justify-center gap-1 text-emerald-400">
                            <CheckCircle className="w-4 h-4" />
                            Success
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-3 text-right text-gray-500 text-sm">
                        {formatDate(redemption.redeemed_at || redemption.created_at)}
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
                <span className="text-purple-400 font-mono">{promoCode.code}</span>?
              </p>
              <p className="text-orange-400/80 text-sm">
                Users will no longer be able to redeem this code. This action cannot be undone.
              </p>
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

export default AdminPromoDetail;

import React, { useEffect, useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { toast } from 'sonner';
import { 
  CheckCircle, 
  XCircle, 
  Clock, 
  Image as ImageIcon,
  AlertTriangle,
  User,
  DollarSign,
  RefreshCw,
  Eye,
  AlertCircle
} from 'lucide-react';

// Centralized Admin API
import { approvalsApi, getErrorMessage } from '../../api/admin';

/**
 * APPROVALS PAGE
 * Human safety net for all pending orders
 */

const AdminApprovals = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pendingDeposits, setPendingDeposits] = useState([]);
  const [pendingWithdrawals, setPendingWithdrawals] = useState([]);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [rejectReason, setRejectReason] = useState('');
  const [processing, setProcessing] = useState(false);

  const fetchPending = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const [depositsRes, withdrawalsRes] = await Promise.allSettled([
        approvalsApi.getPending('deposit'),
        approvalsApi.getPending('withdrawal')
      ]);

      if (depositsRes.status === 'fulfilled') {
        setPendingDeposits(depositsRes.value.data.pending || []);
      } else {
        console.error('Failed to fetch deposits:', depositsRes.reason);
      }
      
      if (withdrawalsRes.status === 'fulfilled') {
        setPendingWithdrawals(withdrawalsRes.value.data.pending || []);
      } else {
        console.error('Failed to fetch withdrawals:', withdrawalsRes.reason);
      }
      
      // Set error only if both failed
      if (depositsRes.status === 'rejected' && withdrawalsRes.status === 'rejected') {
        setError('Failed to load pending approvals');
      }
    } catch (err) {
      console.error('Failed to fetch pending:', err);
      setError(getErrorMessage(err, 'Failed to load pending approvals'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPending();
  }, [fetchPending]);

  const handleAction = async (orderId, action) => {
    if (action === 'reject' && !rejectReason.trim()) {
      toast.error('Please provide a rejection reason');
      return;
    }

    setProcessing(true);
    try {
      await approvalsApi.performAction(
        orderId, 
        action, 
        action === 'reject' ? rejectReason : ''
      );
      
      toast.success(`Order ${action}d successfully`);
      setSelectedOrder(null);
      setRejectReason('');
      fetchPending();
    } catch (err) {
      toast.error(getErrorMessage(err, `Failed to ${action} order`));
    } finally {
      setProcessing(false);
    }
  };

  const OrderCard = ({ order, type }) => (
    <Card 
      className={`bg-gray-900 border-gray-800 hover:border-gray-700 transition cursor-pointer ${
        selectedOrder?.order_id === order.order_id ? 'ring-2 ring-emerald-500' : ''
      }`}
      onClick={() => setSelectedOrder(order)}
    >
      <CardContent className="pt-4">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className={`p-2 rounded-lg ${type === 'deposit' ? 'bg-emerald-500/10' : 'bg-red-500/10'}`}>
              <DollarSign className={`w-4 h-4 ${type === 'deposit' ? 'text-emerald-400' : 'text-red-400'}`} />
            </div>
            <div>
              <p className="text-white font-medium">{order.username}</p>
              <p className="text-gray-500 text-xs">{order.game_name}</p>
            </div>
          </div>
          <div className="text-right">
            <p className={`font-bold ${type === 'deposit' ? 'text-emerald-400' : 'text-red-400'}`}>
              ${order.amount?.toFixed(2)}
            </p>
            {order.bonus_amount > 0 && (
              <p className="text-xs text-blue-400">+${order.bonus_amount?.toFixed(2)} bonus</p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs">
          {order.is_suspicious && (
            <span className="flex items-center gap-1 text-orange-400 bg-orange-500/10 px-2 py-1 rounded">
              <AlertTriangle className="w-3 h-3" />
              Suspicious
            </span>
          )}
          {order.manual_approval_only && (
            <span className="flex items-center gap-1 text-purple-400 bg-purple-500/10 px-2 py-1 rounded">
              <User className="w-3 h-3" />
              Manual Only
            </span>
          )}
          {order.payment_proof_url && (
            <span className="flex items-center gap-1 text-blue-400 bg-blue-500/10 px-2 py-1 rounded">
              <ImageIcon className="w-3 h-3" />
              Has Proof
            </span>
          )}
          <span className="flex items-center gap-1 text-gray-500 ml-auto">
            <Clock className="w-3 h-3" />
            {new Date(order.created_at).toLocaleString()}
          </span>
        </div>
      </CardContent>
    </Card>
  );

  // Loading State
  if (loading && pendingDeposits.length === 0 && pendingWithdrawals.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-emerald-500" />
      </div>
    );
  }

  // Error State
  if (error && pendingDeposits.length === 0 && pendingWithdrawals.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-3" />
          <p className="text-red-400 mb-4">{error}</p>
          <Button onClick={fetchPending} variant="outline">
            Try Again
          </Button>
        </div>
      </div>
    );
  }

  const totalPending = pendingDeposits.length + pendingWithdrawals.length;

  return (
    <div className="space-y-6" data-testid="approvals-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Approvals</h1>
          <p className="text-gray-400 text-sm">
            {totalPending > 0 ? `${totalPending} pending approval${totalPending > 1 ? 's' : ''}` : 'No pending approvals'}
          </p>
        </div>
        <Button onClick={fetchPending} variant="outline" size="sm">
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Order Lists */}
        <div className="lg:col-span-2">
          <Tabs defaultValue="deposits" className="space-y-4">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="deposits" className="flex items-center gap-2">
                <span className="w-5 h-5 rounded-full bg-emerald-500/20 text-emerald-400 text-xs flex items-center justify-center">
                  {pendingDeposits.length}
                </span>
                Deposits
              </TabsTrigger>
              <TabsTrigger value="withdrawals" className="flex items-center gap-2">
                <span className="w-5 h-5 rounded-full bg-red-500/20 text-red-400 text-xs flex items-center justify-center">
                  {pendingWithdrawals.length}
                </span>
                Withdrawals
              </TabsTrigger>
            </TabsList>

            <TabsContent value="deposits" className="space-y-3">
              {pendingDeposits.length === 0 ? (
                <Card className="bg-gray-900 border-gray-800">
                  <CardContent className="py-8 text-center text-gray-500">
                    No pending deposits
                  </CardContent>
                </Card>
              ) : (
                pendingDeposits.map(order => (
                  <OrderCard key={order.order_id} order={order} type="deposit" />
                ))
              )}
            </TabsContent>

            <TabsContent value="withdrawals" className="space-y-3">
              {pendingWithdrawals.length === 0 ? (
                <Card className="bg-gray-900 border-gray-800">
                  <CardContent className="py-8 text-center text-gray-500">
                    No pending withdrawals
                  </CardContent>
                </Card>
              ) : (
                pendingWithdrawals.map(order => (
                  <OrderCard key={order.order_id} order={order} type="withdrawal" />
                ))
              )}
            </TabsContent>
          </Tabs>
        </div>

        {/* Right: Order Detail & Actions */}
        <div className="lg:col-span-1">
          <Card className="bg-gray-900 border-gray-800 sticky top-4">
            <CardHeader>
              <CardTitle className="text-lg">
                {selectedOrder ? 'Order Details' : 'Select an Order'}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {selectedOrder ? (
                <div className="space-y-4">
                  {/* Order Info */}
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-400">Order ID</span>
                      <span className="text-white font-mono text-xs">{selectedOrder.order_id.slice(0, 8)}...</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-400">Username</span>
                      <span className="text-white">{selectedOrder.username}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-400">Game</span>
                      <span className="text-white">{selectedOrder.game_name}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-400">Amount</span>
                      <span className="text-emerald-400 font-bold">${selectedOrder.amount?.toFixed(2)}</span>
                    </div>
                    {selectedOrder.bonus_amount > 0 && (
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-400">Bonus</span>
                        <span className="text-blue-400">+${selectedOrder.bonus_amount?.toFixed(2)}</span>
                      </div>
                    )}
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-400">Total</span>
                      <span className="text-white font-bold">${selectedOrder.total_amount?.toFixed(2)}</span>
                    </div>
                  </div>

                  {/* Payment Proof */}
                  {selectedOrder.payment_proof_url && (
                    <div className="space-y-2">
                      <p className="text-gray-400 text-sm">Payment Proof</p>
                      <a 
                        href={selectedOrder.payment_proof_url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="flex items-center gap-2 p-3 bg-gray-800 rounded-lg hover:bg-gray-700 transition"
                      >
                        <Eye className="w-4 h-4 text-blue-400" />
                        <span className="text-blue-400 text-sm">View Proof Image</span>
                      </a>
                    </div>
                  )}

                  {/* Rejection Reason */}
                  <div className="space-y-2">
                    <p className="text-gray-400 text-sm">Rejection Reason (required for reject)</p>
                    <Input
                      placeholder="Enter reason..."
                      value={rejectReason}
                      onChange={(e) => setRejectReason(e.target.value)}
                      className="bg-gray-800 border-gray-700"
                    />
                  </div>

                  {/* Actions */}
                  <div className="flex gap-2 pt-2">
                    <Button
                      onClick={() => handleAction(selectedOrder.order_id, 'approve')}
                      disabled={processing}
                      className="flex-1 bg-emerald-500 hover:bg-emerald-600"
                      data-testid="approve-btn"
                    >
                      <CheckCircle className="w-4 h-4 mr-2" />
                      Approve
                    </Button>
                    <Button
                      onClick={() => handleAction(selectedOrder.order_id, 'reject')}
                      disabled={processing}
                      variant="destructive"
                      className="flex-1"
                      data-testid="reject-btn"
                    >
                      <XCircle className="w-4 h-4 mr-2" />
                      Reject
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500">
                  <CheckCircle className="w-12 h-12 mx-auto mb-3 opacity-30" />
                  <p>Click on an order to review and approve/reject</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default AdminApprovals;

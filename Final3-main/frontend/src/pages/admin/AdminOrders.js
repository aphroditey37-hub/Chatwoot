/**
 * AdminOrders - Orders Management Page
 * 
 * Features:
 * - View all orders with filters
 * - Detailed order view
 * - Status management
 */

import React, { useEffect, useState, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Tabs, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { 
  FileText, ArrowUpRight, ArrowDownRight, Clock, CheckCircle, XCircle,
  AlertTriangle, RefreshCw, ChevronLeft, DollarSign, User, Gamepad2,
  Image as ImageIcon
} from 'lucide-react';

// Centralized Admin API
import { ordersApi, getErrorMessage } from '../../api';

const AdminOrders = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [orders, setOrders] = useState([]);
  const [total, setTotal] = useState(0);
  const [selectedOrderId, setSelectedOrderId] = useState(null);
  const [orderDetail, setOrderDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [activeTab, setActiveTab] = useState(searchParams.get('type') || 'all');

  const fetchOrders = useCallback(async (type) => {
    setLoading(true);
    setError(null);
    
    try {
      const params = { limit: 50 };
      
      if (type && type !== 'all') {
        if (['deposit', 'withdrawal'].includes(type)) {
          // Backend expects order_type, not type
          params.order_type = type;
        } else if (type === 'pending') {
          // Backend expects status_filter, not status
          params.status_filter = 'pending_review';
        } else if (type === 'voided') {
          params.status_filter = 'voided';
        }
      }
      
      const response = await ordersApi.getAll(params);
      setOrders(response.data.orders || []);
      setTotal(response.data.total || response.data.orders?.length || 0);
    } catch (err) {
      const message = getErrorMessage(err, 'Failed to fetch orders');
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchOrderDetail = useCallback(async (orderId) => {
    setDetailLoading(true);
    try {
      const response = await ordersApi.getById(orderId);
      setOrderDetail(response.data);
    } catch (err) {
      const message = getErrorMessage(err, 'Failed to fetch order detail');
      toast.error(message);
      setOrderDetail(null);
    } finally {
      setDetailLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchOrders(activeTab);
  }, [activeTab, fetchOrders]);

  const handleSelectOrder = (orderId) => {
    setSelectedOrderId(orderId);
    fetchOrderDetail(orderId);
  };

  const handleTabChange = (value) => {
    setActiveTab(value);
    setSearchParams(value !== 'all' ? { type: value } : {});
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'approved':
      case 'completed':
      case 'credited':
        return 'text-emerald-400 bg-emerald-500/10';
      case 'pending_review':
      case 'pending':
      case 'pending_approval':
        return 'text-yellow-400 bg-yellow-500/10';
      case 'rejected':
      case 'failed':
        return 'text-red-400 bg-red-500/10';
      case 'voided':
        return 'text-orange-400 bg-orange-500/10';
      default:
        return 'text-gray-400 bg-gray-500/10';
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Order Detail View
  if (orderDetail) {
    return (
      <div className="space-y-6" data-testid="order-detail">
        <button
          onClick={() => { setOrderDetail(null); setSelectedOrderId(null); }}
          className="flex items-center gap-2 text-gray-400 hover:text-white transition"
        >
          <ChevronLeft className="w-4 h-4" />
          Back to Orders
        </button>

        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">Order Detail</h1>
            <p className="text-gray-400 text-sm font-mono">{orderDetail.order_id}</p>
          </div>
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(orderDetail.status)}`}>
            {orderDetail.status}
          </span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left Column */}
          <div className="space-y-4">
            {/* User Info */}
            <Card className="bg-gray-900 border-gray-800">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-gray-400 flex items-center gap-2">
                  <User className="w-4 h-4" /> User Info
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-400">Username</span>
                  <span className="text-white">{orderDetail.user?.username || orderDetail.username || '-'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">User ID</span>
                  <span className="text-gray-500 text-xs font-mono">{orderDetail.user_id || '-'}</span>
                </div>
                {orderDetail.user?.current_balance && (
                  <div className="flex justify-between">
                    <span className="text-gray-400">Current Balance</span>
                    <span className="text-emerald-400">
                      ${((orderDetail.user.current_balance.real || 0) + (orderDetail.user.current_balance.bonus || 0) + (orderDetail.user.current_balance.play_credits || 0)).toFixed(2)}
                    </span>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Order Amounts */}
            <Card className="bg-gray-900 border-gray-800">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-gray-400 flex items-center gap-2">
                  <DollarSign className="w-4 h-4" /> Amounts
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-400">Order Amount</span>
                  <span className="text-white">${(orderDetail.amount || orderDetail.amounts?.deposit_amount || 0).toFixed(2)}</span>
                </div>
                {orderDetail.amounts?.play_credits_added > 0 && (
                  <div className="flex justify-between">
                    <span className="text-gray-400">Play Credits Added</span>
                    <span className="text-purple-400">${orderDetail.amounts.play_credits_added.toFixed(2)}</span>
                  </div>
                )}
                {orderDetail.amounts?.bonus_added > 0 && (
                  <div className="flex justify-between">
                    <span className="text-gray-400">Bonus Added</span>
                    <span className="text-blue-400">${orderDetail.amounts.bonus_added.toFixed(2)}</span>
                  </div>
                )}
                {orderDetail.amounts?.total_credited > 0 && (
                  <div className="flex justify-between border-t border-gray-800 pt-2">
                    <span className="text-gray-400 font-medium">Total Credited</span>
                    <span className="text-emerald-400 font-bold">${orderDetail.amounts.total_credited.toFixed(2)}</span>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Game Info */}
            {(orderDetail.game || orderDetail.game_name) && (
              <Card className="bg-gray-900 border-gray-800">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm text-gray-400 flex items-center gap-2">
                    <Gamepad2 className="w-4 h-4" /> Game
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-white font-medium">{orderDetail.game?.display_name || orderDetail.game_name}</p>
                  <p className="text-gray-500 text-sm">{orderDetail.game?.name || ''}</p>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Right Column */}
          <div className="space-y-4">
            {/* Consumption (for withdrawals) */}
            {orderDetail.order_type === 'withdrawal' && orderDetail.consumption && (
              <Card className="bg-gray-900 border-gray-800">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm text-gray-400">Consumption Order</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  <p className="text-xs text-gray-500 mb-2">CASH → PLAY CREDITS → BONUS</p>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Cash Consumed</span>
                    <span className="text-white">${(orderDetail.consumption.cash_consumed || 0).toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Play Credits Consumed</span>
                    <span className="text-purple-400">${(orderDetail.consumption.play_credits_consumed || 0).toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Bonus Consumed</span>
                    <span className="text-blue-400">${(orderDetail.consumption.bonus_consumed || 0).toFixed(2)}</span>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Cashout Details */}
            {orderDetail.cashout && (
              <Card className="bg-gray-900 border-gray-800">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm text-gray-400">Cashout Details</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Payout Amount</span>
                    <span className="text-emerald-400 font-bold">${(orderDetail.cashout.payout_amount || 0).toFixed(2)}</span>
                  </div>
                  {orderDetail.cashout.void_amount > 0 && (
                    <>
                      <div className="flex justify-between">
                        <span className="text-gray-400">Voided Amount</span>
                        <span className="text-orange-400">${orderDetail.cashout.void_amount.toFixed(2)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">Void Reason</span>
                        <span className="text-orange-400 text-sm">{orderDetail.cashout.void_reason}</span>
                      </div>
                    </>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Net Profit */}
            {orderDetail.profit && (
              <Card className="bg-gray-900 border-gray-800">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm text-gray-400">Net Profit</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className={`text-3xl font-bold ${(orderDetail.profit.net || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    ${(orderDetail.profit.net || 0).toFixed(2)}
                  </p>
                </CardContent>
              </Card>
            )}

            {/* Payment Proof */}
            {orderDetail.payment_proof_url && (
              <Card className="bg-gray-900 border-gray-800">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm text-gray-400 flex items-center gap-2">
                    <ImageIcon className="w-4 h-4" /> Payment Proof
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <a 
                    href={orderDetail.payment_proof_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block p-3 bg-gray-800 rounded-lg hover:bg-gray-700 transition text-center text-blue-400"
                  >
                    View Proof Image
                  </a>
                </CardContent>
              </Card>
            )}

            {/* Timeline */}
            <Card className="bg-gray-900 border-gray-800">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-gray-400 flex items-center gap-2">
                  <Clock className="w-4 h-4" /> Timeline
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-400">Created</span>
                  <span className="text-white">{formatDate(orderDetail.created_at || orderDetail.timeline?.created_at)}</span>
                </div>
                {orderDetail.timeline?.approved_at && (
                  <div className="flex justify-between">
                    <span className="text-gray-400">Approved</span>
                    <span className="text-white">{formatDate(orderDetail.timeline.approved_at)}</span>
                  </div>
                )}
                {(orderDetail.timeline?.rejection_reason || orderDetail.rejection_reason) && (
                  <div className="flex justify-between">
                    <span className="text-gray-400">Rejection Reason</span>
                    <span className="text-red-400">{orderDetail.timeline?.rejection_reason || orderDetail.rejection_reason}</span>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    );
  }

  // Orders List View
  return (
    <div className="space-y-6" data-testid="orders-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Orders</h1>
          <p className="text-gray-400 text-sm">{total} total orders</p>
        </div>
        <Button onClick={() => fetchOrders(activeTab)} variant="outline" size="sm" disabled={loading}>
          <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Error State */}
      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl flex items-center justify-between">
          <p className="text-red-400">{error}</p>
          <button onClick={() => fetchOrders(activeTab)} className="text-red-400 hover:text-red-300">
            Retry
          </button>
        </div>
      )}

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={handleTabChange}>
        <TabsList className="grid grid-cols-5 w-full">
          <TabsTrigger value="all">All</TabsTrigger>
          <TabsTrigger value="deposit" className="text-emerald-400">Deposits</TabsTrigger>
          <TabsTrigger value="withdrawal" className="text-red-400">Withdrawals</TabsTrigger>
          <TabsTrigger value="pending" className="text-yellow-400">Pending</TabsTrigger>
          <TabsTrigger value="voided" className="text-orange-400">Voided</TabsTrigger>
        </TabsList>
      </Tabs>

      {/* Loading State */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="w-8 h-8 animate-spin text-violet-500" />
        </div>
      ) : orders.length === 0 ? (
        <Card className="bg-gray-900 border-gray-800">
          <CardContent className="py-12 text-center text-gray-500">
            <FileText className="w-12 h-12 mx-auto mb-3 opacity-30" />
            No orders found
          </CardContent>
        </Card>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-800">
                <th className="text-left text-gray-400 text-xs font-medium py-3 px-3">Type</th>
                <th className="text-left text-gray-400 text-xs font-medium py-3 px-3">User</th>
                <th className="text-left text-gray-400 text-xs font-medium py-3 px-3">Game</th>
                <th className="text-right text-gray-400 text-xs font-medium py-3 px-3">Amount</th>
                <th className="text-right text-gray-400 text-xs font-medium py-3 px-3">Bonus</th>
                <th className="text-center text-gray-400 text-xs font-medium py-3 px-3">Status</th>
                <th className="text-right text-gray-400 text-xs font-medium py-3 px-3">Date</th>
              </tr>
            </thead>
            <tbody>
              {orders.map(order => (
                <tr 
                  key={order.order_id}
                  onClick={() => handleSelectOrder(order.order_id)}
                  className="border-b border-gray-800/50 hover:bg-gray-800/30 cursor-pointer"
                >
                  <td className="py-3 px-3">
                    <span className={`flex items-center gap-1 text-xs ${
                      order.order_type === 'deposit' || order.order_type?.includes('load') ? 'text-emerald-400' : 'text-red-400'
                    }`}>
                      {order.order_type === 'deposit' || order.order_type?.includes('load')
                        ? <ArrowUpRight className="w-3 h-3" /> 
                        : <ArrowDownRight className="w-3 h-3" />
                      }
                      {order.order_type}
                    </span>
                  </td>
                  <td className="py-3 px-3 text-white text-sm">
                    {order.username}
                    {order.is_suspicious && (
                      <AlertTriangle className="w-3 h-3 text-orange-400 inline ml-1" />
                    )}
                  </td>
                  <td className="py-3 px-3 text-gray-400 text-sm">{order.game_name || '-'}</td>
                  <td className="py-3 px-3 text-right text-white text-sm">${(order.amount || 0).toFixed(2)}</td>
                  <td className="py-3 px-3 text-right text-blue-400 text-sm">+${(order.bonus_amount || 0).toFixed(2)}</td>
                  <td className="py-3 px-3 text-center">
                    <span className={`px-2 py-1 rounded text-xs ${getStatusColor(order.status)}`}>
                      {order.status}
                    </span>
                  </td>
                  <td className="py-3 px-3 text-right text-gray-500 text-xs">
                    {formatDate(order.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default AdminOrders;

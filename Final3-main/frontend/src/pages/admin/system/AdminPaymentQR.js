/**
 * Admin Payment QR Management
 * Manage QR codes for wallet funding
 * Uses centralized admin API client
 */
import React, { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import { 
  QrCode, Plus, Edit3, Trash2, X, RefreshCw, 
  ToggleLeft, ToggleRight, Star, Upload, Image, AlertCircle
} from 'lucide-react';

// Centralized Admin API
import { systemApi, getErrorMessage } from '../../../api/admin';

const AdminPaymentQR = () => {
  const [loading, setLoading] = useState(true);
  const [qrCodes, setQrCodes] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [editingQR, setEditingQR] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  
  const [formData, setFormData] = useState({
    payment_method: '',
    label: '',
    account_name: '',
    account_number: '',
    image_url: '',
    is_active: true,
    is_default: false
  });

  const fetchQRCodes = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await systemApi.getPaymentQr();
      setQrCodes(response.data.qr_codes || []);
    } catch (err) {
      console.error('Failed to fetch QR codes:', err);
      setError(getErrorMessage(err, 'Failed to load QR codes'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchQRCodes();
  }, [fetchQRCodes]);

  const handleOpenModal = (qr = null) => {
    if (qr) {
      setEditingQR(qr);
      setFormData({
        payment_method: qr.payment_method,
        label: qr.label,
        account_name: qr.account_name || '',
        account_number: qr.account_number || '',
        image_url: qr.image_url,
        is_active: qr.is_active,
        is_default: qr.is_default
      });
    } else {
      setEditingQR(null);
      setFormData({
        payment_method: '',
        label: '',
        account_name: '',
        account_number: '',
        image_url: '',
        is_active: true,
        is_default: false
      });
    }
    setShowModal(true);
  };

  const handleImageUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setFormData({ ...formData, image_url: reader.result });
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.payment_method || !formData.label || !formData.image_url) {
      toast.error('Please fill in all required fields');
      return;
    }

    setSubmitting(true);
    try {
      if (editingQR) {
        await systemApi.updatePaymentQr(editingQR.qr_id, formData);
        toast.success('QR code updated');
      } else {
        await systemApi.createPaymentQr(formData);
        toast.success('QR code created');
      }
      setShowModal(false);
      fetchQRCodes();
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to save QR code'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (qrId) => {
    if (!window.confirm('Are you sure you want to delete this QR code?')) return;
    
    try {
      await systemApi.deletePaymentQr(qrId);
      toast.success('QR code deleted');
      fetchQRCodes();
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to delete QR code'));
    }
  };

  const handleToggleActive = async (qr) => {
    try {
      await systemApi.updatePaymentQr(qr.qr_id, { is_active: !qr.is_active });
      toast.success(qr.is_active ? 'QR code deactivated' : 'QR code activated');
      fetchQRCodes();
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to update QR code'));
    }
  };

  const handleSetDefault = async (qr) => {
    try {
      await systemApi.updatePaymentQr(qr.qr_id, { is_default: true });
      toast.success('Set as default');
      fetchQRCodes();
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to set default'));
    }
  };

  // Group QR codes by payment method
  const groupedQR = qrCodes.reduce((acc, qr) => {
    if (!acc[qr.payment_method]) acc[qr.payment_method] = [];
    acc[qr.payment_method].push(qr);
    return acc;
  }, {});

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 text-emerald-500 animate-spin" />
      </div>
    );
  }

  if (error && qrCodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-3" />
          <p className="text-red-400 mb-4">{error}</p>
          <button 
            onClick={fetchQRCodes} 
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-lg text-white"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="payment-qr-management">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Payment QR Management</h1>
          <p className="text-gray-400 text-sm">Manage QR codes for wallet funding</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={fetchQRCodes}
            className="p-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition"
            data-testid="refresh-qr-btn"
          >
            <RefreshCw className="w-5 h-5 text-gray-400" />
          </button>
          <button
            onClick={() => handleOpenModal()}
            className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg transition"
            data-testid="add-qr-btn"
          >
            <Plus className="w-5 h-5" />
            Add QR Code
          </button>
        </div>
      </div>

      {/* Info Banner */}
      <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-4">
        <p className="text-blue-400 text-sm">
          <strong>Note:</strong> Only ONE QR code can be active per payment method. 
          When you activate a QR, others for the same method will be deactivated.
        </p>
      </div>

      {/* QR Codes by Method */}
      {Object.keys(groupedQR).length === 0 ? (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 text-center">
          <QrCode className="w-16 h-16 text-gray-600 mx-auto mb-4" />
          <h3 className="text-white font-medium mb-2">No Payment QR Codes</h3>
          <p className="text-gray-400 text-sm mb-4">
            Add your first QR code to enable wallet funding for clients.
          </p>
          <button
            onClick={() => handleOpenModal()}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg transition"
          >
            Add QR Code
          </button>
        </div>
      ) : (
        Object.entries(groupedQR).map(([method, codes]) => (
          <div key={method} className="bg-gray-900 border border-gray-800 rounded-xl p-6">
            <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <QrCode className="w-5 h-5 text-emerald-400" />
              {method}
              <span className="text-sm font-normal text-gray-400 ml-2">
                ({codes.length} QR{codes.length !== 1 ? 's' : ''})
              </span>
            </h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {codes.map((qr) => (
                <div 
                  key={qr.qr_id}
                  className={`relative bg-gray-800 rounded-lg p-4 border-2 ${
                    qr.is_active ? 'border-emerald-500/50' : 'border-gray-700'
                  }`}
                  data-testid={`qr-${qr.qr_id}`}
                >
                  {/* Status Badges */}
                  <div className="absolute top-2 right-2 flex gap-1">
                    {qr.is_default && (
                      <span className="px-2 py-0.5 bg-yellow-500/20 text-yellow-400 text-xs rounded-full flex items-center gap-1">
                        <Star className="w-3 h-3" /> Default
                      </span>
                    )}
                    <span className={`px-2 py-0.5 text-xs rounded-full ${
                      qr.is_active 
                        ? 'bg-emerald-500/20 text-emerald-400' 
                        : 'bg-gray-600/20 text-gray-400'
                    }`}>
                      {qr.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>

                  {/* QR Image */}
                  <div className="w-full aspect-square bg-gray-900 rounded-lg mb-3 flex items-center justify-center overflow-hidden">
                    {qr.image_url ? (
                      <img 
                        src={qr.image_url} 
                        alt={qr.label}
                        className="w-full h-full object-contain"
                      />
                    ) : (
                      <Image className="w-12 h-12 text-gray-600" />
                    )}
                  </div>

                  {/* Info */}
                  <h3 className="text-white font-medium">{qr.label}</h3>
                  {qr.account_name && (
                    <p className="text-gray-400 text-sm">{qr.account_name}</p>
                  )}
                  {qr.account_number && (
                    <p className="text-gray-500 text-xs font-mono">{qr.account_number}</p>
                  )}

                  {/* Actions */}
                  <div className="flex gap-2 mt-3">
                    <button
                      onClick={() => handleToggleActive(qr)}
                      className={`flex-1 py-2 rounded-lg text-sm flex items-center justify-center gap-1 ${
                        qr.is_active 
                          ? 'bg-gray-700 text-gray-300' 
                          : 'bg-emerald-600/20 text-emerald-400'
                      }`}
                    >
                      {qr.is_active ? <ToggleRight className="w-4 h-4" /> : <ToggleLeft className="w-4 h-4" />}
                      {qr.is_active ? 'Deactivate' : 'Activate'}
                    </button>
                    <button
                      onClick={() => handleOpenModal(qr)}
                      className="p-2 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg"
                    >
                      <Edit3 className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(qr.qr_id)}
                      className="p-2 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))
      )}

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4">
          <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 w-full max-w-md max-h-[90vh] overflow-auto">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-bold text-white">
                {editingQR ? 'Edit QR Code' : 'Add QR Code'}
              </h3>
              <button onClick={() => setShowModal(false)} className="text-gray-400 hover:text-white">
                <X className="w-6 h-6" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Payment Method *</label>
                <input
                  type="text"
                  value={formData.payment_method}
                  onChange={(e) => setFormData({ ...formData, payment_method: e.target.value })}
                  placeholder="GCash, Maya, BPI, etc."
                  className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white"
                  required
                  data-testid="qr-method-input"
                />
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-1">Label *</label>
                <input
                  type="text"
                  value={formData.label}
                  onChange={(e) => setFormData({ ...formData, label: e.target.value })}
                  placeholder="Main GCash QR"
                  className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white"
                  required
                  data-testid="qr-label-input"
                />
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-1">Account Name</label>
                <input
                  type="text"
                  value={formData.account_name}
                  onChange={(e) => setFormData({ ...formData, account_name: e.target.value })}
                  placeholder="Juan Dela Cruz"
                  className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white"
                />
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-1">Account Number</label>
                <input
                  type="text"
                  value={formData.account_number}
                  onChange={(e) => setFormData({ ...formData, account_number: e.target.value })}
                  placeholder="09123456789"
                  className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white"
                />
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-1">QR Image *</label>
                <div className="border-2 border-dashed border-gray-700 rounded-lg p-4">
                  {formData.image_url ? (
                    <div className="relative">
                      <img src={formData.image_url} alt="QR Preview" className="w-full h-48 object-contain" />
                      <button
                        type="button"
                        onClick={() => setFormData({ ...formData, image_url: '' })}
                        className="absolute top-2 right-2 p-1 bg-red-500 rounded-full text-white"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  ) : (
                    <label className="flex flex-col items-center cursor-pointer py-4">
                      <Upload className="w-8 h-8 text-gray-500 mb-2" />
                      <span className="text-gray-400 text-sm">Click to upload QR image</span>
                      <input
                        type="file"
                        accept="image/*"
                        onChange={handleImageUpload}
                        className="hidden"
                      />
                    </label>
                  )}
                </div>
              </div>

              <div className="space-y-3">
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.is_active}
                    onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                    className="w-4 h-4 rounded border-gray-600 text-emerald-600"
                  />
                  <span className="text-gray-300">Active</span>
                </label>
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.is_default}
                    onChange={(e) => setFormData({ ...formData, is_default: e.target.checked })}
                    className="w-4 h-4 rounded border-gray-600 text-yellow-600"
                  />
                  <span className="text-gray-300">Set as Default</span>
                </label>
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="flex-1 py-2 bg-gray-800 text-gray-300 rounded-lg hover:bg-gray-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="flex-1 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:opacity-50 flex items-center justify-center gap-2"
                  data-testid="save-qr-btn"
                >
                  {submitting && <RefreshCw className="w-4 h-4 animate-spin" />}
                  {editingQR ? 'Update' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminPaymentQR;

/**
 * Admin Promotions Page
 * Manage backend-driven promotional banners for client home
 * 
 * Features:
 * - Create/Edit/Delete promotions
 * - Schedule start/end dates
 * - Set priority for display order
 * - Track views and clicks
 */
import React, { useEffect, useState, useCallback } from 'react';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import {
  RefreshCw, Plus, Edit2, Trash2, Megaphone, Eye, MousePointer,
  Calendar, CheckCircle, Clock, AlertCircle, X
} from 'lucide-react';

import { promotionsApi, getErrorMessage } from '../../api/admin';

const STATUS_COLORS = {
  active: 'bg-green-500/20 text-green-400',
  scheduled: 'bg-blue-500/20 text-blue-400',
  expired: 'bg-gray-500/20 text-gray-400',
  disabled: 'bg-red-500/20 text-red-400',
};

const AdminPromotions = () => {
  const [loading, setLoading] = useState(true);
  const [promotions, setPromotions] = useState([]);
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);
  
  // Modal states
  const [showModal, setShowModal] = useState(false);
  const [editingPromo, setEditingPromo] = useState(null);
  const [processing, setProcessing] = useState(false);
  
  // Form state
  const [form, setForm] = useState({
    title: '',
    subtitle: '',
    description: '',
    image_url: '',
    cta_text: 'Learn More',
    cta_link: '',
    badge_text: '',
    background_color: '#8b5cf6',
    text_color: '#ffffff',
    priority: 0,
    start_date: '',
    end_date: '',
    target_segment: 'all',
    is_active: true,
  });

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [promosRes, statsRes] = await Promise.all([
        promotionsApi.getAll(),
        promotionsApi.getStats().catch(() => ({ data: { stats: {} } })),
      ]);
      setPromotions(promosRes.data.promotions || []);
      setStats(statsRes.data.stats || {});
    } catch (err) {
      console.error('Failed to fetch promotions:', err);
      setError(getErrorMessage(err, 'Failed to load promotions'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const resetForm = () => {
    setForm({
      title: '',
      subtitle: '',
      description: '',
      image_url: '',
      cta_text: 'Learn More',
      cta_link: '',
      badge_text: '',
      background_color: '#8b5cf6',
      text_color: '#ffffff',
      priority: 0,
      start_date: '',
      end_date: '',
      target_segment: 'all',
      is_active: true,
    });
  };

  const openCreateModal = () => {
    setEditingPromo(null);
    resetForm();
    // Set default dates
    const now = new Date();
    const oneWeekLater = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);
    setForm(f => ({
      ...f,
      start_date: now.toISOString().slice(0, 16),
      end_date: oneWeekLater.toISOString().slice(0, 16),
    }));
    setShowModal(true);
  };

  const openEditModal = (promo) => {
    setEditingPromo(promo);
    setForm({
      title: promo.title || '',
      subtitle: promo.subtitle || '',
      description: promo.description || '',
      image_url: promo.image_url || '',
      cta_text: promo.cta_text || 'Learn More',
      cta_link: promo.cta_link || '',
      badge_text: promo.badge_text || '',
      background_color: promo.background_color || '#8b5cf6',
      text_color: promo.text_color || '#ffffff',
      priority: promo.priority || 0,
      start_date: promo.start_date?.slice(0, 16) || '',
      end_date: promo.end_date?.slice(0, 16) || '',
      target_segment: promo.target_segment || 'all',
      is_active: promo.is_active !== false,
    });
    setShowModal(true);
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setProcessing(true);
    
    try {
      const data = {
        ...form,
        start_date: new Date(form.start_date).toISOString(),
        end_date: new Date(form.end_date).toISOString(),
      };
      
      if (editingPromo) {
        await promotionsApi.update(editingPromo.promo_id, data);
        toast.success('Promotion updated');
      } else {
        await promotionsApi.create(data);
        toast.success('Promotion created');
      }
      
      setShowModal(false);
      setEditingPromo(null);
      fetchData();
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to save promotion'));
    } finally {
      setProcessing(false);
    }
  };

  const handleDelete = async (promoId) => {
    if (!window.confirm('Delete this promotion?')) return;
    
    try {
      await promotionsApi.delete(promoId);
      toast.success('Promotion deleted');
      fetchData();
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to delete'));
    }
  };

  const toggleActive = async (promo) => {
    try {
      await promotionsApi.update(promo.promo_id, { is_active: !promo.is_active });
      toast.success(promo.is_active ? 'Promotion disabled' : 'Promotion enabled');
      fetchData();
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to update'));
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-emerald-500" />
      </div>
    );
  }

  if (error && promotions.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-3" />
          <p className="text-red-400 mb-4">{error}</p>
          <button onClick={fetchData} className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-lg text-white">
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="admin-promotions-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-2">
            <Megaphone className="w-7 h-7 text-pink-400" />
            Promotions & Banners
          </h1>
          <p className="text-gray-400 mt-1">Manage client home promotional content</p>
        </div>
        <div className="flex gap-3">
          <button onClick={fetchData} className="p-2.5 bg-gray-800 hover:bg-gray-700 rounded-xl text-gray-400 hover:text-white">
            <RefreshCw className="w-5 h-5" />
          </button>
          <button onClick={openCreateModal} className="flex items-center gap-2 px-4 py-2 bg-pink-500 hover:bg-pink-600 text-white rounded-xl transition" data-testid="create-promo-btn">
            <Plus className="w-5 h-5" />
            New Promotion
          </button>
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-4 gap-4">
          <Card className="bg-gray-900 border-gray-800">
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-green-500/10 rounded-xl">
                  <CheckCircle className="w-6 h-6 text-green-400" />
                </div>
                <div>
                  <p className="text-gray-400 text-sm">Active</p>
                  <p className="text-2xl font-bold text-white">{stats.active || 0}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-gray-900 border-gray-800">
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-blue-500/10 rounded-xl">
                  <Clock className="w-6 h-6 text-blue-400" />
                </div>
                <div>
                  <p className="text-gray-400 text-sm">Scheduled</p>
                  <p className="text-2xl font-bold text-white">{stats.scheduled || 0}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-gray-900 border-gray-800">
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-purple-500/10 rounded-xl">
                  <Eye className="w-6 h-6 text-purple-400" />
                </div>
                <div>
                  <p className="text-gray-400 text-sm">Total Views</p>
                  <p className="text-2xl font-bold text-white">{stats.total_views || 0}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-gray-900 border-gray-800">
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-orange-500/10 rounded-xl">
                  <MousePointer className="w-6 h-6 text-orange-400" />
                </div>
                <div>
                  <p className="text-gray-400 text-sm">Total Clicks</p>
                  <p className="text-2xl font-bold text-white">{stats.total_clicks || 0}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Promotions List */}
      <Card className="bg-gray-900 border-gray-800">
        <CardHeader>
          <CardTitle className="text-lg text-white">All Promotions</CardTitle>
        </CardHeader>
        <CardContent>
          {promotions.length === 0 ? (
            <div className="py-12 text-center">
              <Megaphone className="w-12 h-12 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-500">No promotions yet</p>
              <p className="text-gray-600 text-sm">Create your first promotion to engage clients</p>
            </div>
          ) : (
            <div className="space-y-4">
              {promotions.map((promo) => (
                <div
                  key={promo.promo_id}
                  className="p-4 rounded-xl border transition-all"
                  style={{ 
                    borderColor: promo.status === 'active' ? `${promo.background_color}50` : 'rgb(55, 65, 81)',
                    backgroundColor: promo.status === 'active' ? `${promo.background_color}10` : 'rgba(31, 41, 55, 0.5)',
                  }}
                  data-testid={`promo-${promo.promo_id}`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      {/* Color preview */}
                      <div 
                        className="w-12 h-12 rounded-xl flex items-center justify-center"
                        style={{ backgroundColor: promo.background_color }}
                      >
                        <Megaphone className="w-6 h-6" style={{ color: promo.text_color }} />
                      </div>
                      
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <p className="text-white font-semibold">{promo.title}</p>
                          {promo.badge_text && (
                            <span className="px-2 py-0.5 text-xs bg-gray-700 text-gray-300 rounded-full">
                              {promo.badge_text}
                            </span>
                          )}
                        </div>
                        <p className="text-gray-500 text-sm">{promo.subtitle || 'No subtitle'}</p>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-6">
                      {/* Stats */}
                      <div className="flex gap-4 text-sm">
                        <div className="flex items-center gap-1 text-gray-400">
                          <Eye className="w-4 h-4" />
                          {promo.views || 0}
                        </div>
                        <div className="flex items-center gap-1 text-gray-400">
                          <MousePointer className="w-4 h-4" />
                          {promo.clicks || 0}
                        </div>
                      </div>
                      
                      {/* Priority */}
                      <div className="text-center">
                        <p className="text-xs text-gray-500">Priority</p>
                        <p className="text-white font-mono">{promo.priority}</p>
                      </div>
                      
                      {/* Dates */}
                      <div className="text-right text-sm">
                        <p className="text-gray-500">
                          {new Date(promo.start_date).toLocaleDateString()} - {new Date(promo.end_date).toLocaleDateString()}
                        </p>
                      </div>
                      
                      {/* Status */}
                      <span className={`px-3 py-1 text-xs font-medium rounded-full ${STATUS_COLORS[promo.status] || STATUS_COLORS.disabled}`}>
                        {promo.status?.charAt(0).toUpperCase() + promo.status?.slice(1)}
                      </span>
                      
                      {/* Actions */}
                      <div className="flex gap-2">
                        <button
                          onClick={() => toggleActive(promo)}
                          className={`p-2 rounded-lg transition ${promo.is_active ? 'bg-green-500/20 text-green-400 hover:bg-green-500/30' : 'bg-gray-700 text-gray-400 hover:bg-gray-600'}`}
                          title={promo.is_active ? 'Disable' : 'Enable'}
                        >
                          {promo.is_active ? <CheckCircle className="w-4 h-4" /> : <X className="w-4 h-4" />}
                        </button>
                        <button onClick={() => openEditModal(promo)} className="p-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-gray-300">
                          <Edit2 className="w-4 h-4" />
                        </button>
                        <button onClick={() => handleDelete(promo.promo_id)} className="p-2 bg-red-500/20 hover:bg-red-500/30 rounded-lg text-red-400">
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4 overflow-y-auto">
          <div className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-2xl my-8">
            <div className="px-6 py-4 border-b border-gray-800 flex items-center justify-between">
              <h3 className="text-lg font-bold text-white">
                {editingPromo ? 'Edit Promotion' : 'New Promotion'}
              </h3>
              <button onClick={() => setShowModal(false)} className="p-2 hover:bg-gray-800 rounded-lg text-gray-400">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <form onSubmit={handleSave} className="p-6 space-y-4 max-h-[70vh] overflow-y-auto">
              {/* Preview */}
              <div 
                className="p-4 rounded-xl mb-4"
                style={{ backgroundColor: form.background_color }}
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-white/20 rounded-lg">
                    <Megaphone className="w-6 h-6" style={{ color: form.text_color }} />
                  </div>
                  <div>
                    {form.badge_text && (
                      <span className="inline-block px-2 py-0.5 text-xs font-bold rounded-full mb-1" style={{ backgroundColor: `${form.text_color}20`, color: form.text_color }}>
                        {form.badge_text}
                      </span>
                    )}
                    <h4 className="font-bold" style={{ color: form.text_color }}>{form.title || 'Promotion Title'}</h4>
                    <p className="text-sm opacity-80" style={{ color: form.text_color }}>{form.subtitle || 'Subtitle'}</p>
                  </div>
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-gray-400 text-sm mb-2">Title *</label>
                  <input type="text" required value={form.title} onChange={(e) => setForm(f => ({ ...f, title: e.target.value }))} className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white" placeholder="Summer Bonus Bash" />
                </div>
                <div>
                  <label className="block text-gray-400 text-sm mb-2">Subtitle</label>
                  <input type="text" value={form.subtitle} onChange={(e) => setForm(f => ({ ...f, subtitle: e.target.value }))} className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white" placeholder="Get 50% extra on deposits" />
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-gray-400 text-sm mb-2">Badge Text</label>
                  <input type="text" value={form.badge_text} onChange={(e) => setForm(f => ({ ...f, badge_text: e.target.value }))} className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white" placeholder="NEW" maxLength={30} />
                </div>
                <div>
                  <label className="block text-gray-400 text-sm mb-2">Priority</label>
                  <input type="number" value={form.priority} onChange={(e) => setForm(f => ({ ...f, priority: parseInt(e.target.value) || 0 }))} className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white" min={0} max={100} />
                  <p className="text-gray-500 text-xs mt-1">Higher = shown first</p>
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-gray-400 text-sm mb-2">CTA Button Text</label>
                  <input type="text" value={form.cta_text} onChange={(e) => setForm(f => ({ ...f, cta_text: e.target.value }))} className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white" placeholder="Learn More" />
                </div>
                <div>
                  <label className="block text-gray-400 text-sm mb-2">CTA Link</label>
                  <input type="url" value={form.cta_link} onChange={(e) => setForm(f => ({ ...f, cta_link: e.target.value }))} className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white" placeholder="https://..." />
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-gray-400 text-sm mb-2">Background Color</label>
                  <div className="flex gap-2">
                    <input type="color" value={form.background_color} onChange={(e) => setForm(f => ({ ...f, background_color: e.target.value }))} className="w-12 h-10 rounded cursor-pointer" />
                    <input type="text" value={form.background_color} onChange={(e) => setForm(f => ({ ...f, background_color: e.target.value }))} className="flex-1 px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white font-mono" />
                  </div>
                </div>
                <div>
                  <label className="block text-gray-400 text-sm mb-2">Text Color</label>
                  <div className="flex gap-2">
                    <input type="color" value={form.text_color} onChange={(e) => setForm(f => ({ ...f, text_color: e.target.value }))} className="w-12 h-10 rounded cursor-pointer" />
                    <input type="text" value={form.text_color} onChange={(e) => setForm(f => ({ ...f, text_color: e.target.value }))} className="flex-1 px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white font-mono" />
                  </div>
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-gray-400 text-sm mb-2">Start Date *</label>
                  <input type="datetime-local" required value={form.start_date} onChange={(e) => setForm(f => ({ ...f, start_date: e.target.value }))} className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white" />
                </div>
                <div>
                  <label className="block text-gray-400 text-sm mb-2">End Date *</label>
                  <input type="datetime-local" required value={form.end_date} onChange={(e) => setForm(f => ({ ...f, end_date: e.target.value }))} className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white" />
                </div>
              </div>
              
              <div>
                <label className="block text-gray-400 text-sm mb-2">Description</label>
                <textarea value={form.description} onChange={(e) => setForm(f => ({ ...f, description: e.target.value }))} className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white" rows={2} placeholder="Optional description..." />
              </div>
              
              <div className="flex items-center gap-3">
                <input type="checkbox" id="is_active" checked={form.is_active} onChange={(e) => setForm(f => ({ ...f, is_active: e.target.checked }))} className="w-4 h-4 rounded" />
                <label htmlFor="is_active" className="text-gray-300">Active (will show to clients if within date range)</label>
              </div>
              
              <div className="flex gap-3 pt-4 border-t border-gray-800">
                <button type="button" onClick={() => setShowModal(false)} className="flex-1 py-2.5 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg">
                  Cancel
                </button>
                <button type="submit" disabled={processing} className="flex-1 py-2.5 bg-pink-500 hover:bg-pink-600 disabled:opacity-50 text-white rounded-lg flex items-center justify-center gap-2">
                  {processing && <RefreshCw className="w-4 h-4 animate-spin" />}
                  {processing ? 'Saving...' : editingPromo ? 'Update' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminPromotions;

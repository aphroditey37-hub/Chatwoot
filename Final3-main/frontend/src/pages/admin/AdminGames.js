/**
 * Admin Games Management Page
 * Manage game availability and downloads
 * Uses centralized admin API client
 */
import React, { useEffect, useState, useCallback } from 'react';
import { toast } from 'sonner';
import { 
  Gamepad2, Plus, Edit2, Power, X, Download, Star, Clock, 
  CheckCircle, XCircle, Smartphone, Globe, Apple, Eye, Link,
  RefreshCw, AlertCircle
} from 'lucide-react';

// Centralized Admin API
import { gamesApi, getErrorMessage } from '../../api/admin';

const AdminGames = () => {
  const [loading, setLoading] = useState(true);
  const [games, setGames] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [editingGame, setEditingGame] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [form, setForm] = useState({
    name: '',
    description: '',
    tagline: '',
    category: '',
    download_url: '',
    icon_url: '',
    thumbnail: '',
    platforms: ['android'],
    availability_status: 'available',
    show_credentials: true,
    allow_recharge: true,
    is_featured: false
  });

  const fetchGames = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await gamesApi.getAll();
      // Handle both array and object response structures
      const gamesData = Array.isArray(response.data) ? response.data : (response.data.games || []);
      // Map backend fields to frontend expected fields
      const mappedGames = gamesData.map(game => ({
        id: game.game_id || game.id,
        name: game.display_name || game.game_name || game.name,
        game_name: game.game_name,
        description: game.description || '',
        tagline: game.tagline || '',
        category: game.category || '',
        download_url: game.download_url || '',
        icon_url: game.icon_url || '',
        thumbnail: game.thumbnail || '',
        platforms: game.platforms || ['android'],
        availability_status: game.availability_status || 'available',
        show_credentials: game.show_credentials !== false,
        allow_recharge: game.allow_recharge !== false,
        is_featured: game.is_featured || false,
        is_active: game.is_active !== false,
        config: game.config || {},
        analytics: game.analytics || {}
      }));
      setGames(mappedGames);
    } catch (err) {
      console.error('Failed to fetch games:', err);
      setError(getErrorMessage(err, 'Failed to load games'));
      setGames([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchGames();
  }, [fetchGames]);

  const handleSubmit = async () => {
    if (!form.name || !form.description) {
      toast.error('Please fill name and description');
      return;
    }

    setSubmitting(true);
    try {
      if (editingGame) {
        await gamesApi.update(editingGame.id, form);
        toast.success('Game updated successfully');
      } else {
        // Note: gamesApi doesn't have create, would need to be added
        toast.error('Create not implemented in API yet');
        setSubmitting(false);
        return;
      }
      setShowModal(false);
      setEditingGame(null);
      resetForm();
      fetchGames();
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to save game'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleToggleActive = async (game) => {
    try {
      await gamesApi.update(game.id, { is_active: !game.is_active });
      toast.success(game.is_active ? 'Game deactivated' : 'Game activated');
      fetchGames();
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to update game'));
    }
  };

  const handleAvailabilityChange = async (game, status) => {
    try {
      await gamesApi.update(game.id, { availability_status: status });
      toast.success('Availability updated');
      fetchGames();
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to update availability'));
    }
  };

  const handleToggleFeatured = async (game) => {
    try {
      await gamesApi.update(game.id, { is_featured: !game.is_featured });
      toast.success(game.is_featured ? 'Removed from featured' : 'Marked as featured');
      fetchGames();
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to update'));
    }
  };

  const resetForm = () => {
    setForm({
      name: '',
      description: '',
      tagline: '',
      category: '',
      download_url: '',
      icon_url: '',
      thumbnail: '',
      platforms: ['android'],
      availability_status: 'available',
      show_credentials: true,
      allow_recharge: true,
      is_featured: false
    });
  };

  const openEditModal = (game) => {
    setEditingGame(game);
    setForm({
      name: game.name,
      description: game.description,
      tagline: game.tagline || '',
      category: game.category || '',
      download_url: game.download_url || '',
      icon_url: game.icon_url || '',
      thumbnail: game.thumbnail || '',
      platforms: game.platforms || ['android'],
      availability_status: game.availability_status || 'available',
      show_credentials: game.show_credentials !== false,
      allow_recharge: game.allow_recharge !== false,
      is_featured: game.is_featured || false
    });
    setShowModal(true);
  };

  const openCreateModal = () => {
    setEditingGame(null);
    resetForm();
    setShowModal(true);
  };

  const handlePlatformToggle = (platform) => {
    if (form.platforms.includes(platform)) {
      setForm({ ...form, platforms: form.platforms.filter(p => p !== platform) });
    } else {
      setForm({ ...form, platforms: [...form.platforms, platform] });
    }
  };

  const getAvailabilityIcon = (status) => {
    switch (status) {
      case 'available': return <CheckCircle className="w-4 h-4 text-emerald-400" />;
      case 'maintenance': return <Clock className="w-4 h-4 text-yellow-400" />;
      case 'unavailable': return <XCircle className="w-4 h-4 text-red-400" />;
      default: return <CheckCircle className="w-4 h-4 text-emerald-400" />;
    }
  };

  const getAvailabilityColor = (status) => {
    switch (status) {
      case 'available': return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
      case 'maintenance': return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
      case 'unavailable': return 'bg-red-500/20 text-red-400 border-red-500/30';
      default: return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-emerald-500" />
      </div>
    );
  }

  if (error && games.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-3" />
          <p className="text-red-400 mb-4">{error}</p>
          <button 
            onClick={fetchGames} 
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-lg text-white"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="admin-games-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Games Management</h1>
          <p className="text-gray-400 text-sm">{games.length} total games • Manage availability and downloads</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={fetchGames}
            className="p-2 bg-gray-800 hover:bg-gray-700 text-gray-400 hover:text-white rounded-lg"
            data-testid="refresh-games-btn"
          >
            <RefreshCw className="w-5 h-5" />
          </button>
          <a
            href="/games"
            target="_blank"
            className="px-4 py-2 bg-gray-800 text-gray-300 rounded-lg hover:bg-gray-700 transition flex items-center gap-2"
          >
            <Eye className="w-4 h-4" />
            Public View
          </a>
          <button
            onClick={openCreateModal}
            className="px-4 py-2 bg-emerald-500 text-white rounded-lg hover:bg-emerald-600 transition flex items-center gap-2"
            data-testid="add-game-btn"
          >
            <Plus className="w-4 h-4" />
            Add Game
          </button>
        </div>
      </div>

      {/* Games Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {games.length === 0 ? (
          <div className="col-span-full bg-gray-900 border border-gray-800 rounded-xl p-8 text-center">
            <Gamepad2 className="w-12 h-12 text-gray-600 mx-auto mb-4" />
            <p className="text-gray-400">No games created yet</p>
          </div>
        ) : (
          games.map((game) => (
            <div
              key={game.id}
              className={`bg-gray-900 border rounded-xl overflow-hidden transition-all ${
                game.is_active ? 'border-gray-800 hover:border-gray-700' : 'border-red-500/20 opacity-60'
              }`}
              data-testid={`game-${game.id}`}
            >
              {/* Card Header */}
              <div className="p-4 border-b border-gray-800">
                <div className="flex items-start gap-4">
                  {/* Icon */}
                  <div className="w-16 h-16 bg-gradient-to-br from-gray-800 to-gray-900 rounded-xl flex items-center justify-center flex-shrink-0">
                    {game.icon_url || game.thumbnail ? (
                      <img src={game.icon_url || game.thumbnail} alt={game.name} className="w-full h-full object-cover rounded-xl" />
                    ) : (
                      <Gamepad2 className="w-8 h-8 text-gray-600" />
                    )}
                  </div>
                  
                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="text-white font-semibold truncate">{game.name}</h3>
                      {game.is_featured && (
                        <Star className="w-4 h-4 text-purple-400 fill-purple-400" />
                      )}
                    </div>
                    {game.tagline && (
                      <p className="text-gray-500 text-sm truncate">{game.tagline}</p>
                    )}
                    {game.category && (
                      <span className="inline-block px-2 py-0.5 bg-gray-800 text-gray-400 text-xs rounded mt-1">
                        {game.category}
                      </span>
                    )}
                  </div>

                  {/* Status Badges */}
                  <div className="flex flex-col items-end gap-2">
                    <span className={`px-2 py-1 text-xs rounded-full border flex items-center gap-1 ${getAvailabilityColor(game.availability_status)}`}>
                      {getAvailabilityIcon(game.availability_status)}
                      {game.availability_status || 'available'}
                    </span>
                    {!game.is_active && (
                      <span className="px-2 py-1 bg-red-500/10 text-red-400 text-xs rounded-full">
                        Inactive
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Card Body */}
              <div className="p-4 space-y-3">
                <p className="text-gray-400 text-sm line-clamp-2">{game.description}</p>

                {/* Platforms & Download */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {(game.platforms || ['android']).map(p => (
                      <span key={p} className="flex items-center gap-1 text-gray-500 text-xs">
                        {p === 'android' && <Smartphone className="w-3 h-3" />}
                        {p === 'ios' && <Apple className="w-3 h-3" />}
                        {p === 'web' && <Globe className="w-3 h-3" />}
                      </span>
                    ))}
                  </div>
                  {game.download_url && (
                    <a 
                      href={game.download_url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-emerald-400 text-xs flex items-center gap-1 hover:underline"
                    >
                      <Download className="w-3 h-3" />
                      Download Link
                    </a>
                  )}
                </div>

                {/* Settings Toggles */}
                <div className="flex items-center gap-4 text-xs">
                  <span className={`flex items-center gap-1 ${game.show_credentials !== false ? 'text-emerald-400' : 'text-gray-500'}`}>
                    <Eye className="w-3 h-3" />
                    {game.show_credentials !== false ? 'Creds Visible' : 'Creds Hidden'}
                  </span>
                  <span className={`flex items-center gap-1 ${game.allow_recharge !== false ? 'text-emerald-400' : 'text-gray-500'}`}>
                    <Link className="w-3 h-3" />
                    {game.allow_recharge !== false ? 'Recharge On' : 'Recharge Off'}
                  </span>
                </div>
              </div>

              {/* Card Actions */}
              <div className="p-4 bg-gray-950 border-t border-gray-800 flex gap-2">
                <button
                  onClick={() => openEditModal(game)}
                  className="flex-1 py-2 bg-gray-800 text-white rounded-lg hover:bg-gray-700 transition flex items-center justify-center gap-1 text-sm"
                  data-testid={`edit-game-${game.id}`}
                >
                  <Edit2 className="w-4 h-4" />
                  Edit
                </button>
                
                {/* Availability Dropdown */}
                <select
                  value={game.availability_status || 'available'}
                  onChange={(e) => handleAvailabilityChange(game, e.target.value)}
                  className="py-2 px-3 bg-gray-800 text-white rounded-lg text-sm border-none focus:ring-2 focus:ring-emerald-500"
                  data-testid={`availability-${game.id}`}
                >
                  <option value="available">✅ Available</option>
                  <option value="maintenance">⏳ Maintenance</option>
                  <option value="unavailable">❌ Unavailable</option>
                </select>

                <button
                  onClick={() => handleToggleFeatured(game)}
                  className={`py-2 px-3 rounded-lg transition flex items-center justify-center text-sm ${
                    game.is_featured
                      ? 'bg-purple-500/20 text-purple-400'
                      : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                  }`}
                  title={game.is_featured ? 'Remove from featured' : 'Mark as featured'}
                  data-testid={`feature-game-${game.id}`}
                >
                  <Star className={`w-4 h-4 ${game.is_featured ? 'fill-current' : ''}`} />
                </button>

                <button
                  onClick={() => handleToggleActive(game)}
                  className={`py-2 px-3 rounded-lg transition flex items-center justify-center text-sm ${
                    game.is_active
                      ? 'bg-red-500/10 text-red-400 hover:bg-red-500/20'
                      : 'bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20'
                  }`}
                  title={game.is_active ? 'Deactivate' : 'Activate'}
                  data-testid={`toggle-game-${game.id}`}
                >
                  <Power className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4 overflow-y-auto" onClick={() => setShowModal(false)}>
          <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 w-full max-w-lg my-8" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-bold text-white">
                {editingGame ? 'Edit Game' : 'Add New Game'}
              </h3>
              <button onClick={() => setShowModal(false)} className="text-gray-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="space-y-4 max-h-[70vh] overflow-y-auto pr-2">
              {/* Basic Info */}
              <div>
                <label className="block text-gray-400 text-sm mb-1">Name *</label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full px-3 py-2 bg-black border border-gray-700 rounded-lg text-white focus:border-emerald-500 focus:outline-none"
                  placeholder="Game name"
                  data-testid="game-name-input"
                />
              </div>

              <div>
                <label className="block text-gray-400 text-sm mb-1">Tagline</label>
                <input
                  type="text"
                  value={form.tagline}
                  onChange={(e) => setForm({ ...form, tagline: e.target.value })}
                  className="w-full px-3 py-2 bg-black border border-gray-700 rounded-lg text-white focus:border-emerald-500 focus:outline-none"
                  placeholder="Short tagline"
                />
              </div>

              <div>
                <label className="block text-gray-400 text-sm mb-1">Description *</label>
                <textarea
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  className="w-full px-3 py-2 bg-black border border-gray-700 rounded-lg text-white resize-none focus:border-emerald-500 focus:outline-none"
                  rows={3}
                  placeholder="Game description"
                  data-testid="game-description-input"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-gray-400 text-sm mb-1">Category</label>
                  <input
                    type="text"
                    value={form.category}
                    onChange={(e) => setForm({ ...form, category: e.target.value })}
                    className="w-full px-3 py-2 bg-black border border-gray-700 rounded-lg text-white focus:border-emerald-500 focus:outline-none"
                    placeholder="e.g., Slots"
                  />
                </div>
                <div>
                  <label className="block text-gray-400 text-sm mb-1">Availability</label>
                  <select
                    value={form.availability_status}
                    onChange={(e) => setForm({ ...form, availability_status: e.target.value })}
                    className="w-full px-3 py-2 bg-black border border-gray-700 rounded-lg text-white focus:border-emerald-500 focus:outline-none"
                  >
                    <option value="available">✅ Available</option>
                    <option value="maintenance">⏳ Maintenance</option>
                    <option value="unavailable">❌ Unavailable</option>
                  </select>
                </div>
              </div>

              {/* Download & Media */}
              <div>
                <label className="block text-gray-400 text-sm mb-1">Download URL</label>
                <input
                  type="url"
                  value={form.download_url}
                  onChange={(e) => setForm({ ...form, download_url: e.target.value })}
                  className="w-full px-3 py-2 bg-black border border-gray-700 rounded-lg text-white focus:border-emerald-500 focus:outline-none"
                  placeholder="https://..."
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-gray-400 text-sm mb-1">Icon URL</label>
                  <input
                    type="url"
                    value={form.icon_url}
                    onChange={(e) => setForm({ ...form, icon_url: e.target.value })}
                    className="w-full px-3 py-2 bg-black border border-gray-700 rounded-lg text-white focus:border-emerald-500 focus:outline-none"
                    placeholder="Icon image URL"
                  />
                </div>
                <div>
                  <label className="block text-gray-400 text-sm mb-1">Thumbnail URL</label>
                  <input
                    type="url"
                    value={form.thumbnail}
                    onChange={(e) => setForm({ ...form, thumbnail: e.target.value })}
                    className="w-full px-3 py-2 bg-black border border-gray-700 rounded-lg text-white focus:border-emerald-500 focus:outline-none"
                    placeholder="Thumbnail image URL"
                  />
                </div>
              </div>

              {/* Platforms */}
              <div>
                <label className="block text-gray-400 text-sm mb-2">Platforms</label>
                <div className="flex gap-2">
                  {['android', 'ios', 'web'].map(platform => (
                    <button
                      key={platform}
                      type="button"
                      onClick={() => handlePlatformToggle(platform)}
                      className={`px-4 py-2 rounded-lg flex items-center gap-2 text-sm transition ${
                        form.platforms.includes(platform)
                          ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                          : 'bg-gray-800 text-gray-400 border border-gray-700'
                      }`}
                    >
                      {platform === 'android' && <Smartphone className="w-4 h-4" />}
                      {platform === 'ios' && <Apple className="w-4 h-4" />}
                      {platform === 'web' && <Globe className="w-4 h-4" />}
                      {platform.charAt(0).toUpperCase() + platform.slice(1)}
                    </button>
                  ))}
                </div>
              </div>

              {/* Toggles */}
              <div className="space-y-3 pt-2 border-t border-gray-800">
                <label className="flex items-center justify-between cursor-pointer">
                  <span className="text-gray-300">Show credentials to clients</span>
                  <input
                    type="checkbox"
                    checked={form.show_credentials}
                    onChange={(e) => setForm({ ...form, show_credentials: e.target.checked })}
                    className="w-5 h-5 rounded border-gray-600 bg-gray-800 text-emerald-500 focus:ring-emerald-500"
                  />
                </label>
                <label className="flex items-center justify-between cursor-pointer">
                  <span className="text-gray-300">Allow recharge</span>
                  <input
                    type="checkbox"
                    checked={form.allow_recharge}
                    onChange={(e) => setForm({ ...form, allow_recharge: e.target.checked })}
                    className="w-5 h-5 rounded border-gray-600 bg-gray-800 text-emerald-500 focus:ring-emerald-500"
                  />
                </label>
                <label className="flex items-center justify-between cursor-pointer">
                  <span className="text-gray-300">Featured game</span>
                  <input
                    type="checkbox"
                    checked={form.is_featured}
                    onChange={(e) => setForm({ ...form, is_featured: e.target.checked })}
                    className="w-5 h-5 rounded border-gray-600 bg-gray-800 text-purple-500 focus:ring-purple-500"
                  />
                </label>
              </div>
            </div>

            <div className="flex gap-2 pt-4 mt-4 border-t border-gray-800">
              <button
                onClick={() => setShowModal(false)}
                className="flex-1 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmit}
                disabled={submitting}
                className="flex-1 py-2 bg-emerald-500 text-white rounded-lg hover:bg-emerald-600 transition disabled:opacity-50 flex items-center justify-center gap-2"
                data-testid="save-game-btn"
              >
                {submitting && <RefreshCw className="w-4 h-4 animate-spin" />}
                {editingGame ? 'Update Game' : 'Create Game'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminGames;

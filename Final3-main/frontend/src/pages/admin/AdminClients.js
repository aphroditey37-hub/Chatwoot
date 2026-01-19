import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Users, Eye, RefreshCw, AlertCircle } from 'lucide-react';

// Centralized Admin API
import { usersApi, getErrorMessage } from '../../api/admin';

const AdminClients = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [clients, setClients] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  const fetchClients = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const params = {};
      if (statusFilter !== 'all') {
        params.status = statusFilter;
      }
      const response = await usersApi.getAll(params);
      setClients(response.data.clients || []);
    } catch (err) {
      console.error('Failed to fetch clients:', err);
      setError(getErrorMessage(err, 'Failed to load clients'));
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    fetchClients();
  }, [fetchClients]);

  const filteredClients = (clients || []).filter(client => {
    const searchLower = searchTerm.toLowerCase();
    return (
      client.display_name?.toLowerCase().includes(searchLower) ||
      client.username?.toLowerCase().includes(searchLower) ||
      client.referral_code?.toLowerCase().includes(searchLower)
    );
  });

  const getStatusBadge = (status) => {
    switch (status) {
      case 'active':
        return <span className="px-2 py-1 text-xs rounded-full bg-emerald-500/10 text-emerald-400">Active</span>;
      case 'frozen':
        return <span className="px-2 py-1 text-xs rounded-full bg-yellow-500/10 text-yellow-400">Frozen</span>;
      case 'banned':
        return <span className="px-2 py-1 text-xs rounded-full bg-red-500/10 text-red-400">Banned</span>;
      default:
        return <span className="px-2 py-1 text-xs rounded-full bg-gray-500/10 text-gray-400">{status}</span>;
    }
  };

  // Loading State
  if (loading && clients.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-emerald-500" />
      </div>
    );
  }

  // Error State
  if (error && clients.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-3" />
          <p className="text-red-400 mb-4">{error}</p>
          <button 
            onClick={fetchClients}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg transition"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="admin-clients-page">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Clients</h1>
          <p className="text-gray-400 text-sm">{clients.length} total clients</p>
        </div>
        <div className="flex gap-2">
          <button 
            onClick={fetchClients}
            disabled={loading}
            className="p-2 bg-gray-800 hover:bg-gray-700 text-gray-400 hover:text-white rounded-lg transition-colors"
            title="Refresh"
          >
            <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button 
            onClick={() => navigate('/admin/clients/new')}
            className="px-4 py-2 bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg font-medium transition-colors flex items-center gap-2"
          >
            <Users className="w-4 h-4" />
            Add Client
          </button>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={fetchClients} className="text-red-300 hover:text-white">Retry</button>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search clients..."
            className="w-full pl-10 pr-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-emerald-500"
        >
          <option value="all">All Status</option>
          <option value="active">Active</option>
          <option value="frozen">Frozen</option>
          <option value="banned">Banned</option>
        </select>
      </div>

      {/* Clients List */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        {filteredClients.length === 0 ? (
          <div className="p-8 text-center">
            <Users className="w-12 h-12 text-gray-600 mx-auto mb-4" />
            <p className="text-gray-400">No clients found</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-800">
                  <th className="text-left px-4 py-3 text-gray-400 font-medium text-sm">Client</th>
                  <th className="text-left px-4 py-3 text-gray-400 font-medium text-sm">Referral Code</th>
                  <th className="text-left px-4 py-3 text-gray-400 font-medium text-sm">Status</th>
                  <th className="text-left px-4 py-3 text-gray-400 font-medium text-sm">Joined</th>
                  <th className="text-right px-4 py-3 text-gray-400 font-medium text-sm">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredClients.map((client) => (
                  <tr
                    key={client.user_id || client.client_id}
                    className="border-b border-gray-800 hover:bg-gray-800/50 transition-colors"
                  >
                    <td className="px-4 py-3">
                      <div>
                        <p className="text-white font-medium">{client.display_name}</p>
                        <p className="text-gray-500 text-xs">{(client.user_id || client.client_id)?.slice(0, 8)}...</p>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="font-mono text-emerald-400">{client.referral_code}</span>
                    </td>
                    <td className="px-4 py-3">
                      {getStatusBadge(client.status || (client.is_active ? 'active' : 'inactive'))}
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-sm">
                      {new Date(client.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => navigate(`/admin/clients/${client.user_id || client.client_id}`)}
                        className="p-2 text-gray-400 hover:text-emerald-400 hover:bg-gray-800 rounded-lg transition-colors"
                        title="View Details"
                        data-testid={`view-client-${client.user_id || client.client_id}`}
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminClients;

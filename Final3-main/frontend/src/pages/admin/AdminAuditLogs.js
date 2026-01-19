/**
 * AdminAuditLogs - Audit Logs Page
 * 
 * Features:
 * - View all admin actions
 * - Pagination
 * - Filter by action type
 */

import React, { useEffect, useState, useCallback } from 'react';
import { toast } from 'sonner';
import { FileText, User, Clock, Filter, ChevronLeft, ChevronRight, RefreshCw, AlertCircle } from 'lucide-react';

// Centralized Admin API
import { auditApi, getErrorMessage } from '../../api';

const AdminAuditLogs = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [logs, setLogs] = useState([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [actionFilter, setActionFilter] = useState('');
  
  const limit = 20;

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const params = { page, limit };
      if (actionFilter) params.action = actionFilter;
      
      const response = await auditApi.getLogs(params);
      setLogs(response.data.logs || []);
      setTotalPages(Math.ceil((response.data.total || 0) / limit) || 1);
    } catch (err) {
      const message = getErrorMessage(err, 'Failed to fetch audit logs');
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }, [page, actionFilter]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  const getActionColor = (action) => {
    const actionStr = String(action || '').toLowerCase();
    if (actionStr.includes('create') || actionStr.includes('approve')) return 'text-emerald-400 bg-emerald-400/10';
    if (actionStr.includes('update') || actionStr.includes('assign')) return 'text-blue-400 bg-blue-400/10';
    if (actionStr.includes('delete') || actionStr.includes('revoke') || actionStr.includes('ban') || actionStr.includes('reject')) return 'text-red-400 bg-red-400/10';
    if (actionStr.includes('login') || actionStr.includes('auth')) return 'text-violet-400 bg-violet-400/10';
    return 'text-gray-400 bg-gray-400/10';
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  const actionTypes = [
    { value: '', label: 'All Actions' },
    { value: 'create', label: 'Create' },
    { value: 'update', label: 'Update' },
    { value: 'delete', label: 'Delete' },
    { value: 'approve', label: 'Approve' },
    { value: 'reject', label: 'Reject' },
    { value: 'login', label: 'Login' },
    { value: 'ban', label: 'Ban/Suspend' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Audit Logs</h1>
          <p className="text-gray-400 text-sm">Track all admin actions in the system</p>
        </div>
        <button
          onClick={fetchLogs}
          disabled={loading}
          className="p-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
        >
          <RefreshCw className={`w-5 h-5 text-gray-400 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4 p-4 bg-gray-900 border border-gray-800 rounded-xl">
        <Filter className="w-5 h-5 text-gray-500" />
        <select
          value={actionFilter}
          onChange={(e) => { setActionFilter(e.target.value); setPage(1); }}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-violet-500"
        >
          {actionTypes.map(type => (
            <option key={type.value} value={type.value}>{type.label}</option>
          ))}
        </select>
        <span className="text-sm text-gray-500">
          {logs.length} logs displayed
        </span>
      </div>

      {/* Error State */}
      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl flex items-center justify-between">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-400" />
            <p className="text-red-400">{error}</p>
          </div>
          <button
            onClick={fetchLogs}
            className="px-3 py-1 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30"
          >
            Retry
          </button>
        </div>
      )}

      {/* Loading State */}
      {loading && !error && (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-violet-500"></div>
        </div>
      )}

      {/* Logs List */}
      {!loading && !error && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          {logs.length === 0 ? (
            <div className="p-8 text-center">
              <FileText className="w-12 h-12 text-gray-600 mx-auto mb-4" />
              <p className="text-gray-400">No audit logs found</p>
              <p className="text-gray-600 text-sm mt-1">Admin actions will appear here</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-800">
              {logs.map((log, index) => (
                <div key={log.log_id || log.id || index} className="p-4 hover:bg-gray-800/50 transition-colors">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-3 flex-1 min-w-0">
                      <div className="w-10 h-10 bg-gray-800 rounded-full flex items-center justify-center shrink-0">
                        <User className="w-5 h-5 text-gray-400" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-medium text-white">
                            {log.admin_username || log.performed_by || 'System'}
                          </span>
                          <span className={`px-2 py-0.5 rounded text-xs font-medium ${getActionColor(log.action)}`}>
                            {log.action}
                          </span>
                        </div>
                        <p className="text-gray-400 text-sm mt-1 truncate">
                          {typeof log.details === 'string' 
                            ? log.details 
                            : (log.description || `${log.action} on ${log.entity_type || 'entity'}`)}
                        </p>
                        {log.target_id && (
                          <p className="text-gray-600 text-xs mt-1 font-mono">
                            Target: {log.target_id}
                          </p>
                        )}
                        {log.ip_address && (
                          <p className="text-gray-600 text-xs font-mono">
                            IP: {log.ip_address}
                          </p>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-1.5 text-gray-500 text-sm whitespace-nowrap">
                      <Clock className="w-4 h-4" />
                      {formatDate(log.created_at || log.timestamp)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Pagination */}
      {!loading && logs.length > 0 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-gray-500">
            Page {page} of {totalPages}
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="p-2 bg-gray-800 hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors"
            >
              <ChevronLeft className="w-5 h-5 text-gray-400" />
            </button>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="p-2 bg-gray-800 hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors"
            >
              <ChevronRight className="w-5 h-5 text-gray-400" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminAuditLogs;

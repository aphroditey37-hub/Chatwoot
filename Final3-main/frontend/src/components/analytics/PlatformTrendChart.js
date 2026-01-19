/**
 * Platform Trend Chart Component
 * Displays platform performance trends on admin dashboard
 * Uses centralized admin API client
 */
import React, { useEffect, useState, useCallback } from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, 
  Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import { Filter, RefreshCw } from 'lucide-react';

// Centralized Admin API
import { analyticsApi } from '../../api/admin';

const METRICS = [
  { key: 'deposits', label: 'Deposits', color: '#10b981' },
  { key: 'withdrawals_paid', label: 'Withdrawals Paid', color: '#ef4444' },
  { key: 'net_profit', label: 'Net Profit', color: '#3b82f6' },
  { key: 'bonus_issued', label: 'Bonus Issued', color: '#8b5cf6' },
  { key: 'bonus_voided', label: 'Bonus Voided', color: '#f97316' },
  { key: 'active_clients', label: 'Active Clients', color: '#06b6d4', isCount: true }
];

const PlatformTrendChart = () => {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [selectedMetrics, setSelectedMetrics] = useState(['deposits', 'withdrawals_paid', 'net_profit']);
  const [filters, setFilters] = useState({
    days: 30,
    game: 'all',
    client_segment: 'all'
  });
  const [showFilters, setShowFilters] = useState(false);

  const fetchTrendData = useCallback(async () => {
    setLoading(true);
    try {
      // Pass all filter values to API
      const response = await analyticsApi.getPlatformTrends({
        days: filters.days,
        game: filters.game,
        client_segment: filters.client_segment
      });
      setData(response.data);
    } catch (err) {
      console.error('Failed to fetch trend data:', err);
      // Graceful degradation
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [filters.days, filters.game, filters.client_segment]);

  useEffect(() => {
    fetchTrendData();
  }, [fetchTrendData]);

  const toggleMetric = (metricKey) => {
    if (selectedMetrics.includes(metricKey)) {
      if (selectedMetrics.length > 1) {
        setSelectedMetrics(selectedMetrics.filter(m => m !== metricKey));
      }
    } else {
      if (selectedMetrics.length < 3) {
        setSelectedMetrics([...selectedMetrics, metricKey]);
      }
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const formatTooltipValue = (value, name) => {
    const metric = METRICS.find(m => m.label === name);
    if (metric?.isCount) return [value, name];
    return [`$${value.toFixed(2)}`, name];
  };

  if (loading && !data) {
    return (
      <div className="bg-gray-900/50 border border-gray-800 rounded-2xl p-6">
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="w-8 h-8 animate-spin text-emerald-500" />
        </div>
      </div>
    );
  }

  // Graceful degradation if data failed to load
  if (!data) {
    return (
      <div className="bg-gray-900/50 border border-gray-800 rounded-2xl p-6" data-testid="platform-trend-chart">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-lg font-semibold text-white">Platform Performance Trend</h3>
            <p className="text-gray-500 text-sm">Trend data unavailable</p>
          </div>
          <button
            onClick={fetchTrendData}
            className="p-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-gray-400 hover:text-white"
          >
            <RefreshCw className="w-5 h-5" />
          </button>
        </div>
        <div className="flex items-center justify-center h-64">
          <p className="text-gray-500">Unable to load trend data</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gray-900/50 border border-gray-800 rounded-2xl p-6" data-testid="platform-trend-chart">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold text-white">Platform Performance Trend</h3>
          <p className="text-gray-500 text-sm">
            {filters.days} day view • {data?.trend_data?.length || 0} data points
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`p-2 rounded-lg transition-colors ${showFilters ? 'bg-emerald-500/20 text-emerald-400' : 'bg-gray-800 text-gray-400 hover:text-white'}`}
          >
            <Filter className="w-5 h-5" />
          </button>
          <button
            onClick={fetchTrendData}
            className="p-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-gray-400 hover:text-white"
          >
            <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Filters */}
      {showFilters && (
        <div className="grid grid-cols-3 gap-4 mb-6 p-4 bg-gray-800/50 rounded-xl">
          <div>
            <label className="block text-gray-400 text-xs mb-1">Date Range</label>
            <select
              value={filters.days}
              onChange={(e) => setFilters({...filters, days: parseInt(e.target.value)})}
              className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white text-sm"
            >
              <option value={7}>Last 7 days</option>
              <option value={14}>Last 14 days</option>
              <option value={30}>Last 30 days</option>
              <option value={60}>Last 60 days</option>
              <option value={90}>Last 90 days</option>
            </select>
          </div>
          <div>
            <label className="block text-gray-400 text-xs mb-1">Game</label>
            <select
              value={filters.game}
              onChange={(e) => setFilters({...filters, game: e.target.value})}
              className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white text-sm"
            >
              <option value="all">All Games</option>
              {data?.available_games?.map(g => (
                <option key={g} value={g}>{g}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-gray-400 text-xs mb-1">Client Segment</label>
            <select
              value={filters.client_segment}
              onChange={(e) => setFilters({...filters, client_segment: e.target.value})}
              className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white text-sm"
            >
              <option value="all">All Clients</option>
              <option value="referred">Referred</option>
              <option value="non_referred">Non-referred</option>
              <option value="high_risk">High Risk</option>
            </select>
          </div>
        </div>
      )}

      {/* Metric Toggles */}
      <div className="flex flex-wrap gap-2 mb-6">
        {METRICS.map(metric => (
          <button
            key={metric.key}
            onClick={() => toggleMetric(metric.key)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
              selectedMetrics.includes(metric.key)
                ? 'text-white'
                : 'bg-gray-800 text-gray-500 hover:text-gray-300'
            }`}
            style={{
              backgroundColor: selectedMetrics.includes(metric.key) ? `${metric.color}30` : undefined,
              borderColor: selectedMetrics.includes(metric.key) ? metric.color : undefined,
              border: selectedMetrics.includes(metric.key) ? '1px solid' : '1px solid transparent'
            }}
          >
            <span 
              className="inline-block w-2 h-2 rounded-full mr-2"
              style={{ backgroundColor: metric.color }}
            />
            {metric.label}
          </button>
        ))}
        <span className="text-gray-600 text-xs self-center ml-2">
          (Select up to 3)
        </span>
      </div>

      {/* Chart */}
      <div className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data?.trend_data || []}>
            <defs>
              {METRICS.map(metric => (
                <linearGradient key={metric.key} id={`gradient-${metric.key}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={metric.color} stopOpacity={0.3}/>
                  <stop offset="95%" stopColor={metric.color} stopOpacity={0}/>
                </linearGradient>
              ))}
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis 
              dataKey="date" 
              tickFormatter={formatDate}
              stroke="#6b7280"
              tick={{ fill: '#9ca3af', fontSize: 11 }}
            />
            <YAxis 
              stroke="#6b7280"
              tick={{ fill: '#9ca3af', fontSize: 11 }}
              tickFormatter={(v) => `$${v >= 1000 ? (v/1000).toFixed(0) + 'k' : v}`}
            />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: '#1f2937', 
                border: '1px solid #374151',
                borderRadius: '8px'
              }}
              labelStyle={{ color: '#9ca3af' }}
              formatter={formatTooltipValue}
              labelFormatter={(label) => formatDate(label)}
            />
            <Legend />
            {selectedMetrics.map(metricKey => {
              const metric = METRICS.find(m => m.key === metricKey);
              return (
                <Area
                  key={metricKey}
                  type="monotone"
                  dataKey={metricKey}
                  name={metric.label}
                  stroke={metric.color}
                  fill={`url(#gradient-${metricKey})`}
                  strokeWidth={2}
                />
              );
            })}
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Totals */}
      {data?.totals && (
        <div className="grid grid-cols-5 gap-4 mt-6 pt-4 border-t border-gray-800">
          <div className="text-center">
            <p className="text-emerald-400 font-bold text-lg">${data.totals.deposits?.toLocaleString()}</p>
            <p className="text-gray-500 text-xs">Total Deposits</p>
          </div>
          <div className="text-center">
            <p className="text-red-400 font-bold text-lg">${data.totals.withdrawals_paid?.toLocaleString()}</p>
            <p className="text-gray-500 text-xs">Total Withdrawals</p>
          </div>
          <div className="text-center">
            <p className={`font-bold text-lg ${data.totals.net_profit >= 0 ? 'text-blue-400' : 'text-red-400'}`}>
              ${data.totals.net_profit?.toLocaleString()}
            </p>
            <p className="text-gray-500 text-xs">Net Profit</p>
          </div>
          <div className="text-center">
            <p className="text-purple-400 font-bold text-lg">${data.totals.bonus_issued?.toLocaleString()}</p>
            <p className="text-gray-500 text-xs">Bonus Issued</p>
          </div>
          <div className="text-center">
            <p className="text-orange-400 font-bold text-lg">${data.totals.bonus_voided?.toLocaleString()}</p>
            <p className="text-gray-500 text-xs">Bonus Voided</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default PlatformTrendChart;

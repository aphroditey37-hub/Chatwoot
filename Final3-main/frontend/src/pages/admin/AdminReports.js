import React, { useEffect, useState, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { 
  BarChart3, RefreshCw, DollarSign, TrendingUp, Ban, Gamepad2, 
  AlertTriangle, Shield, PieChart, Activity, AlertCircle
} from 'lucide-react';

// Centralized Admin API
import { reportsApi, analyticsApi, getErrorMessage } from '../../api/admin';

const AdminReports = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [balanceFlow, setBalanceFlow] = useState(null);
  const [profitByGame, setProfitByGame] = useState([]);
  const [voids, setVoids] = useState(null);
  const [riskExposure, setRiskExposure] = useState(null);
  const [advancedMetrics, setAdvancedMetrics] = useState(null);

  const activeTab = searchParams.get('tab') || 'flow';

  const fetchReports = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const [flowRes, gameRes, voidRes, riskRes, advRes] = await Promise.allSettled([
        reportsApi.getBalanceFlow(30),
        reportsApi.getProfitByGame(),
        reportsApi.getVoids(30),
        analyticsApi.getRiskExposure(),
        analyticsApi.getAdvancedMetrics()
      ]);
      
      if (flowRes.status === 'fulfilled') setBalanceFlow(flowRes.value.data);
      if (gameRes.status === 'fulfilled') setProfitByGame(gameRes.value.data.by_game || []);
      if (voidRes.status === 'fulfilled') setVoids(voidRes.value.data);
      if (riskRes.status === 'fulfilled') setRiskExposure(riskRes.value.data);
      if (advRes.status === 'fulfilled') setAdvancedMetrics(advRes.value.data);
      
      // Set error only if all failed
      const allFailed = [flowRes, gameRes, voidRes, riskRes, advRes].every(r => r.status === 'rejected');
      if (allFailed) {
        setError('Failed to load reports');
      }
    } catch (err) {
      console.error('Failed to fetch reports:', err);
      setError(getErrorMessage(err, 'Failed to load reports'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchReports();
  }, [fetchReports]);

  const handleTabChange = (value) => {
    setSearchParams({ tab: value });
  };

  // Loading State
  if (loading && !balanceFlow && profitByGame.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-emerald-500" />
      </div>
    );
  }

  // Error State
  if (error && !balanceFlow && profitByGame.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-3" />
          <p className="text-red-400 mb-4">{error}</p>
          <button 
            onClick={fetchReports}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg transition"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="reports-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <BarChart3 className="w-6 h-6 text-blue-400" />
            Reports
          </h1>
          <p className="text-gray-400 text-sm">Financial truth & inspection</p>
        </div>
        <button onClick={fetchReports} className="p-2 hover:bg-gray-800 rounded-lg text-gray-400 hover:text-white">
          <RefreshCw className="w-5 h-5" />
        </button>
      </div>

      <Tabs value={activeTab} onValueChange={handleTabChange} className="space-y-4">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="flow">Balance Flow</TabsTrigger>
          <TabsTrigger value="game">By Game</TabsTrigger>
          <TabsTrigger value="voids">Voids</TabsTrigger>
          <TabsTrigger value="risk" className="text-orange-400">Risk & Exposure</TabsTrigger>
          <TabsTrigger value="advanced">Advanced</TabsTrigger>
        </TabsList>

        {/* Balance Flow */}
        <TabsContent value="flow">
          <Card className="bg-gray-900 border-gray-800">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <DollarSign className="w-5 h-5 text-emerald-400" />
                Balance Flow (Last {balanceFlow?.period_days || 30} Days)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <div className="p-4 bg-gray-800 rounded-lg">
                  <p className="text-gray-400 text-sm">Total Deposits</p>
                  <p className="text-2xl font-bold text-emerald-400">${balanceFlow?.flow?.deposits?.toFixed(2) || '0.00'}</p>
                </div>
                <div className="p-4 bg-gray-800 rounded-lg">
                  <p className="text-gray-400 text-sm">Bonus Granted</p>
                  <p className="text-2xl font-bold text-blue-400">${balanceFlow?.flow?.bonus_granted?.toFixed(2) || '0.00'}</p>
                </div>
                <div className="p-4 bg-gray-800 rounded-lg">
                  <p className="text-gray-400 text-sm">Play Credits</p>
                  <p className="text-2xl font-bold text-purple-400">${balanceFlow?.flow?.play_credits_granted?.toFixed(2) || '0.00'}</p>
                </div>
                <div className="p-4 bg-gray-800 rounded-lg">
                  <p className="text-gray-400 text-sm">Total Payouts</p>
                  <p className="text-2xl font-bold text-red-400">${balanceFlow?.flow?.payouts?.toFixed(2) || '0.00'}</p>
                </div>
                <div className="p-4 bg-gray-800 rounded-lg">
                  <p className="text-gray-400 text-sm">Total Voided</p>
                  <p className="text-2xl font-bold text-orange-400">${balanceFlow?.flow?.voided?.toFixed(2) || '0.00'}</p>
                </div>
                <div className="p-4 bg-emerald-500/10 rounded-lg border border-emerald-500/30">
                  <p className="text-emerald-400 text-sm">Net Profit</p>
                  <p className="text-2xl font-bold text-emerald-400">${balanceFlow?.flow?.net_profit?.toFixed(2) || '0.00'}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Profit by Game */}
        <TabsContent value="game">
          <Card className="bg-gray-900 border-gray-800">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Gamepad2 className="w-5 h-5 text-purple-400" />
                Profit by Game
              </CardTitle>
            </CardHeader>
            <CardContent>
              {profitByGame.length === 0 ? (
                <p className="text-gray-500 text-center py-8">No game data yet</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-gray-800">
                        <th className="text-left text-gray-400 text-xs py-2 px-3">Game</th>
                        <th className="text-right text-gray-400 text-xs py-2 px-3">Deposits</th>
                        <th className="text-right text-gray-400 text-xs py-2 px-3">Payouts</th>
                        <th className="text-right text-gray-400 text-xs py-2 px-3">Bonus</th>
                        <th className="text-right text-gray-400 text-xs py-2 px-3">Voided</th>
                        <th className="text-right text-gray-400 text-xs py-2 px-3">Net Profit</th>
                      </tr>
                    </thead>
                    <tbody>
                      {profitByGame.map((g, i) => (
                        <tr key={i} className="border-b border-gray-800/50">
                          <td className="py-3 px-3 text-white">{g.game}</td>
                          <td className="py-3 px-3 text-right text-emerald-400">${g.deposits?.toFixed(2)}</td>
                          <td className="py-3 px-3 text-right text-red-400">${g.payouts?.toFixed(2)}</td>
                          <td className="py-3 px-3 text-right text-blue-400">${g.bonus?.toFixed(2)}</td>
                          <td className="py-3 px-3 text-right text-orange-400">${g.voided?.toFixed(2)}</td>
                          <td className={`py-3 px-3 text-right font-bold ${g.net_profit >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                            ${g.net_profit?.toFixed(2)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Void Report */}
        <TabsContent value="voids">
          <Card className="bg-gray-900 border-gray-800">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Ban className="w-5 h-5 text-orange-400" />
                Void Report (Last {voids?.period_days || 30} Days)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="mb-4 p-4 bg-orange-500/10 rounded-lg border border-orange-500/30">
                <p className="text-orange-400 text-sm">Total Voided</p>
                <p className="text-2xl font-bold text-orange-400">${voids?.total_voided?.toFixed(2) || '0.00'}</p>
              </div>
              {voids?.voids?.length === 0 ? (
                <p className="text-gray-500 text-center py-8">No voids in this period</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-gray-800">
                        <th className="text-left text-gray-400 text-xs py-2 px-3">User</th>
                        <th className="text-left text-gray-400 text-xs py-2 px-3">Game</th>
                        <th className="text-right text-gray-400 text-xs py-2 px-3">Amount</th>
                        <th className="text-left text-gray-400 text-xs py-2 px-3">Reason</th>
                        <th className="text-right text-gray-400 text-xs py-2 px-3">Date</th>
                      </tr>
                    </thead>
                    <tbody>
                      {voids?.voids?.map((v, i) => (
                        <tr key={i} className="border-b border-gray-800/50">
                          <td className="py-3 px-3 text-white">{v.username}</td>
                          <td className="py-3 px-3 text-gray-400">{v.game}</td>
                          <td className="py-3 px-3 text-right text-orange-400">${v.amount?.toFixed(2)}</td>
                          <td className="py-3 px-3 text-gray-500 text-sm">{v.reason}</td>
                          <td className="py-3 px-3 text-right text-gray-500 text-sm">
                            {v.date ? new Date(v.date).toLocaleDateString() : '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Risk & Exposure - NEW */}
        <TabsContent value="risk">
          <div className="space-y-6">
            {/* Section A: Platform Exposure */}
            <Card className="bg-gray-900 border-gray-800">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Shield className="w-5 h-5 text-blue-400" />
                  Platform Exposure
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-3 md:grid-cols-6 gap-4">
                  <div className="p-4 bg-gray-800 rounded-lg">
                    <p className="text-gray-400 text-xs">Cash Balance</p>
                    <p className="text-xl font-bold text-emerald-400">${riskExposure?.platform_exposure?.total_cash_balance?.toLocaleString() || '0'}</p>
                  </div>
                  <div className="p-4 bg-gray-800 rounded-lg">
                    <p className="text-gray-400 text-xs">Bonus Balance</p>
                    <p className="text-xl font-bold text-purple-400">${riskExposure?.platform_exposure?.total_bonus_balance?.toLocaleString() || '0'}</p>
                  </div>
                  <div className="p-4 bg-gray-800 rounded-lg">
                    <p className="text-gray-400 text-xs">Play Credits</p>
                    <p className="text-xl font-bold text-blue-400">${riskExposure?.platform_exposure?.total_play_credits?.toLocaleString() || '0'}</p>
                  </div>
                  <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-lg">
                    <p className="text-emerald-400 text-xs">Combined</p>
                    <p className="text-xl font-bold text-emerald-400">${riskExposure?.platform_exposure?.combined_balance?.toLocaleString() || '0'}</p>
                  </div>
                  <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
                    <p className="text-red-400 text-xs">Locked</p>
                    <p className="text-xl font-bold text-red-400">${riskExposure?.platform_exposure?.locked_balance?.toLocaleString() || '0'}</p>
                  </div>
                  <div className="p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
                    <p className="text-yellow-400 text-xs">Withdrawable</p>
                    <p className="text-xl font-bold text-yellow-400">${riskExposure?.platform_exposure?.withdrawable_balance?.toLocaleString() || '0'}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Section B: Probable Max Cashout */}
            <Card className="bg-gray-900 border-gray-800">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-purple-400" />
                  Probable Max Cashout
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-3 gap-4 mb-6">
                  <div className="p-4 bg-purple-500/10 border border-purple-500/30 rounded-lg">
                    <p className="text-purple-400 text-xs">Total Probable Max</p>
                    <p className="text-2xl font-bold text-purple-400">${riskExposure?.probable_max_cashout?.total_probable_max?.toLocaleString() || '0'}</p>
                    <p className="text-gray-500 text-xs mt-1">@ {riskExposure?.probable_max_cashout?.multiplier_settings?.max || 3}x cap</p>
                  </div>
                  <div className="p-4 bg-gray-800 rounded-lg">
                    <p className="text-gray-400 text-xs">Cash-Only Max</p>
                    <p className="text-2xl font-bold text-white">${riskExposure?.probable_max_cashout?.cash_only_max?.toLocaleString() || '0'}</p>
                  </div>
                  <div className="p-4 bg-gray-800 rounded-lg">
                    <p className="text-gray-400 text-xs">Bonus-Inclusive Max</p>
                    <p className="text-2xl font-bold text-white">${riskExposure?.probable_max_cashout?.bonus_inclusive_max?.toLocaleString() || '0'}</p>
                  </div>
                </div>

                {/* By Game */}
                <h4 className="text-gray-400 text-sm font-medium mb-3">Breakdown by Game</h4>
                <div className="overflow-x-auto mb-6">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-gray-800">
                        <th className="text-left text-gray-400 text-xs py-2 px-3">Game</th>
                        <th className="text-right text-gray-400 text-xs py-2 px-3">Deposited</th>
                        <th className="text-right text-gray-400 text-xs py-2 px-3">Withdrawn</th>
                        <th className="text-right text-gray-400 text-xs py-2 px-3">Max Exposure</th>
                      </tr>
                    </thead>
                    <tbody>
                      {riskExposure?.probable_max_cashout?.by_game?.map((g, i) => (
                        <tr key={i} className="border-b border-gray-800/50">
                          <td className="py-2 px-3 text-white">{g.display_name || g.game}</td>
                          <td className="py-2 px-3 text-right text-emerald-400">${g.total_deposited?.toLocaleString()}</td>
                          <td className="py-2 px-3 text-right text-red-400">${g.total_withdrawn?.toLocaleString()}</td>
                          <td className="py-2 px-3 text-right text-purple-400 font-medium">${g.max_exposure?.toLocaleString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* By Tier */}
                <h4 className="text-gray-400 text-sm font-medium mb-3">Breakdown by Client Tier</h4>
                <div className="grid grid-cols-3 gap-4">
                  {riskExposure?.probable_max_cashout?.by_tier?.map((t, i) => (
                    <div key={i} className="p-4 bg-gray-800 rounded-lg">
                      <p className="text-gray-400 text-xs capitalize">{t.tier} Clients</p>
                      <p className="text-lg font-bold text-white">{t.client_count}</p>
                      <p className="text-gray-500 text-xs mt-1">Max: ${t.max_cashout?.toLocaleString()}</p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Section C: Bonus Risk */}
            <Card className="bg-gray-900 border-gray-800">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5 text-orange-400" />
                  Bonus Risk
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-4 gap-4">
                  <div className="p-4 bg-purple-500/10 rounded-lg">
                    <p className="text-purple-400 text-xs">Bonus Issued</p>
                    <p className="text-xl font-bold text-purple-400">${riskExposure?.bonus_risk?.bonus_issued?.toLocaleString() || '0'}</p>
                  </div>
                  <div className="p-4 bg-emerald-500/10 rounded-lg">
                    <p className="text-emerald-400 text-xs">Bonus Converted</p>
                    <p className="text-xl font-bold text-emerald-400">${riskExposure?.bonus_risk?.bonus_converted?.toLocaleString() || '0'}</p>
                  </div>
                  <div className="p-4 bg-orange-500/10 rounded-lg">
                    <p className="text-orange-400 text-xs">Bonus Voided</p>
                    <p className="text-xl font-bold text-orange-400">${riskExposure?.bonus_risk?.bonus_voided?.toLocaleString() || '0'}</p>
                  </div>
                  <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
                    <p className="text-red-400 text-xs">Bonus at Risk</p>
                    <p className="text-xl font-bold text-red-400">${riskExposure?.bonus_risk?.bonus_at_risk?.toLocaleString() || '0'}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Section D: Client Risk Table */}
            <Card className="bg-gray-900 border-gray-800">
              <CardHeader>
                <CardTitle className="text-white">Top 10 Clients by Balance</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-gray-800">
                        <th className="text-left text-gray-400 text-xs py-2 px-3">Client</th>
                        <th className="text-right text-gray-400 text-xs py-2 px-3">Cash</th>
                        <th className="text-right text-gray-400 text-xs py-2 px-3">Bonus</th>
                        <th className="text-right text-gray-400 text-xs py-2 px-3">Total</th>
                        <th className="text-right text-gray-400 text-xs py-2 px-3">Deposited</th>
                        <th className="text-right text-gray-400 text-xs py-2 px-3">Max Cashout</th>
                        <th className="text-center text-gray-400 text-xs py-2 px-3">Flags</th>
                      </tr>
                    </thead>
                    <tbody>
                      {riskExposure?.tables?.client_risk?.map((c, i) => (
                        <tr key={i} className="border-b border-gray-800/50">
                          <td className="py-2 px-3 text-white">{c.username}</td>
                          <td className="py-2 px-3 text-right text-emerald-400">${c.cash_balance?.toLocaleString()}</td>
                          <td className="py-2 px-3 text-right text-purple-400">${c.bonus_balance?.toLocaleString()}</td>
                          <td className="py-2 px-3 text-right text-white font-medium">${c.total_balance?.toLocaleString()}</td>
                          <td className="py-2 px-3 text-right text-gray-400">${c.total_deposited?.toLocaleString()}</td>
                          <td className="py-2 px-3 text-right text-yellow-400">${c.max_eligible_cashout?.toLocaleString()}</td>
                          <td className="py-2 px-3 text-center">
                            {c.is_suspicious && <span className="text-red-400 text-xs mr-1">⚠️</span>}
                            {c.withdraw_locked && <span className="text-yellow-400 text-xs">🔒</span>}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>

            {/* Section D: Game Risk Table */}
            <Card className="bg-gray-900 border-gray-800">
              <CardHeader>
                <CardTitle className="text-white">Game Risk Overview</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-gray-800">
                        <th className="text-left text-gray-400 text-xs py-2 px-3">Game</th>
                        <th className="text-right text-gray-400 text-xs py-2 px-3">Players</th>
                        <th className="text-right text-gray-400 text-xs py-2 px-3">In</th>
                        <th className="text-right text-gray-400 text-xs py-2 px-3">Out</th>
                        <th className="text-right text-gray-400 text-xs py-2 px-3">Net Profit</th>
                        <th className="text-right text-gray-400 text-xs py-2 px-3">Bonus</th>
                        <th className="text-right text-gray-400 text-xs py-2 px-3">Voided</th>
                      </tr>
                    </thead>
                    <tbody>
                      {riskExposure?.tables?.game_risk?.map((g, i) => (
                        <tr key={i} className="border-b border-gray-800/50">
                          <td className="py-2 px-3 text-white">{g.display_name || g.game}</td>
                          <td className="py-2 px-3 text-right text-gray-400">{g.active_players}</td>
                          <td className="py-2 px-3 text-right text-emerald-400">${g.total_in?.toLocaleString()}</td>
                          <td className="py-2 px-3 text-right text-red-400">${g.total_out?.toLocaleString()}</td>
                          <td className={`py-2 px-3 text-right font-medium ${g.net_profit >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                            ${g.net_profit?.toLocaleString()}
                          </td>
                          <td className="py-2 px-3 text-right text-purple-400">${g.bonus_given?.toLocaleString()}</td>
                          <td className="py-2 px-3 text-right text-orange-400">${g.voided?.toLocaleString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Advanced Metrics - NEW */}
        <TabsContent value="advanced">
          <Card className="bg-gray-900 border-gray-800">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="w-5 h-5 text-cyan-400" />
                Advanced Efficiency Metrics ({advancedMetrics?.period_days || 30} Days)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-6">
                {advancedMetrics?.metrics && Object.entries(advancedMetrics.metrics).map(([key, metric]) => (
                  <div key={key} className="p-5 bg-gray-800 rounded-xl">
                    <p className="text-gray-400 text-xs mb-2 capitalize">{key.replace(/_/g, ' ')}</p>
                    <p className="text-3xl font-bold text-white mb-1">
                      {metric.value?.toFixed(1)}{metric.unit === 'percent' ? '%' : metric.unit === 'x' ? 'x' : ''}
                      {metric.unit === 'hours' && <span className="text-lg text-gray-400 ml-1">hrs</span>}
                    </p>
                    <p className="text-gray-500 text-xs">{metric.description}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default AdminReports;

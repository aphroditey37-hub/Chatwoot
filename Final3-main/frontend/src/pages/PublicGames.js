import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { 
  Gamepad2, Search, 
  CheckCircle, 
  ChevronRight, Sparkles, Lock, RefreshCw
} from 'lucide-react';

// Centralized API
import { gamesApi } from '../api/endpoints';

const PublicGames = () => {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  
  const [games, setGames] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('all');

  const fetchGames = useCallback(async () => {
    try {
      const response = await gamesApi.getPublicGames();
      setGames(response.data.games || response.data || []);
    } catch (error) {
      console.error('Failed to fetch games:', error);
      setGames([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchGames();
  }, [fetchGames]);

  const filteredGames = games.filter(game => {
    const matchesSearch = game.display_name?.toLowerCase().includes(search.toLowerCase()) ||
                         game.game_name?.toLowerCase().includes(search.toLowerCase());
    const matchesFilter = filter === 'all' || 
                         (filter === 'available' && game.is_active);
    return matchesSearch && matchesFilter;
  });

  const handleRecharge = (gameId, gameName) => {
    if (isAuthenticated) {
      navigate(`/portal/load-game?game=${gameName}`);
    } else {
      navigate(`/login?redirect=/portal/load-game&game=${gameName}`);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-950 via-gray-900 to-black">
      {/* Hero Header */}
      <div className="bg-gradient-to-r from-emerald-900/30 via-purple-900/20 to-blue-900/30 border-b border-gray-800">
        <div className="max-w-6xl mx-auto px-4 py-12 text-center">
          <div className="flex justify-center mb-4">
            <div className="w-16 h-16 bg-gradient-to-br from-emerald-500 to-purple-600 rounded-2xl flex items-center justify-center shadow-lg shadow-emerald-500/20">
              <Gamepad2 className="w-8 h-8 text-white" />
            </div>
          </div>
          <h1 className="text-4xl md:text-5xl font-bold text-white mb-3">
            Available Games
          </h1>
          <p className="text-gray-400 text-lg max-w-xl mx-auto">
            Browse our selection of games and start playing
          </p>
          <p className="text-gray-500 text-sm mt-2">
            <Lock className="w-3 h-3 inline mr-1" />
            Login required for deposits and withdrawals
          </p>
        </div>
      </div>

      {/* Search & Filters */}
      <div className="sticky top-0 z-40 bg-gray-900/95 backdrop-blur-sm border-b border-gray-800">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex flex-col md:flex-row gap-4">
            {/* Search */}
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search games..."
                className="w-full pl-10 pr-4 py-3 bg-gray-800 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500"
                data-testid="games-search"
              />
            </div>

            {/* Filter Pills */}
            <div className="flex gap-2 overflow-x-auto pb-2 md:pb-0">
              <button
                onClick={() => setFilter('all')}
                className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition ${
                  filter === 'all'
                    ? 'bg-emerald-500 text-white'
                    : 'bg-gray-800 text-gray-400 hover:text-white'
                }`}
                data-testid="filter-all"
              >
                All Games
              </button>
              <button
                onClick={() => setFilter('available')}
                className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition flex items-center gap-1 ${
                  filter === 'available'
                    ? 'bg-emerald-500 text-white'
                    : 'bg-gray-800 text-gray-400 hover:text-white'
                }`}
                data-testid="filter-available"
              >
                <CheckCircle className="w-3 h-3" />
                Available
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Games Grid */}
      <div className="max-w-6xl mx-auto px-4 py-8">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <RefreshCw className="w-8 h-8 text-emerald-500 animate-spin" />
          </div>
        ) : filteredGames.length === 0 ? (
          <div className="text-center py-20">
            <Gamepad2 className="w-16 h-16 text-gray-600 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">No games found</h3>
            <p className="text-gray-400">Try adjusting your search or filters</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredGames.map(game => (
              <GameCard 
                key={game.game_id} 
                game={game}
                onRecharge={handleRecharge}
              />
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <footer className="border-t border-gray-800 mt-12">
        <div className="max-w-6xl mx-auto px-4 py-12">
          <div className="text-center">
            <h3 className="text-xl font-semibold text-white mb-2">Need help?</h3>
            <p className="text-gray-400 mb-6">Contact support for assistance</p>
            <p className="text-gray-600 text-sm mt-8">
              © 2024 Gaming Platform. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
};

// Game Card Component
const GameCard = ({ game, onRecharge }) => {
  return (
    <div 
      className="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden hover:border-gray-700 transition group" 
      data-testid={`game-card-${game.game_name}`}
    >
      {/* Game Image/Icon */}
      <div className="relative h-40 bg-gradient-to-br from-gray-800 to-gray-900 flex items-center justify-center">
        <Gamepad2 className="w-16 h-16 text-gray-700" />
        
        {/* Status Badge */}
        <div className={`absolute top-3 right-3 flex items-center gap-1 px-2 py-1 border rounded-full text-xs font-medium ${
          game.is_active 
            ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
            : 'bg-red-500/20 text-red-400 border-red-500/30'
        }`}>
          <CheckCircle className="w-3 h-3" />
          {game.is_active ? 'Active' : 'Inactive'}
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        <h3 className="text-lg font-bold text-white mb-1">{game.display_name}</h3>
        <p className="text-gray-400 text-sm mb-3">{game.description || game.game_name}</p>
        
        {/* Game Limits Info */}
        <div className="grid grid-cols-2 gap-2 mb-4 text-xs">
          <div className="bg-gray-800 rounded-lg p-2">
            <span className="text-gray-500 block">Min Deposit</span>
            <span className="text-white font-medium">${game.min_recharge_amount}</span>
          </div>
          <div className="bg-gray-800 rounded-lg p-2">
            <span className="text-gray-500 block">Max Deposit</span>
            <span className="text-white font-medium">${game.max_recharge_amount}</span>
          </div>
        </div>

        {/* Bonus Info */}
        {game.bonus_rules?.first_deposit && (
          <div className="flex items-center gap-2 mb-4 p-2 bg-emerald-500/10 border border-emerald-500/20 rounded-lg">
            <Sparkles className="w-4 h-4 text-emerald-400" />
            <span className="text-emerald-400 text-sm">
              {game.bonus_rules.first_deposit.percent_bonus}% First Deposit Bonus
            </span>
          </div>
        )}

        {/* Action Buttons */}
        <button
          onClick={() => onRecharge(game.game_id, game.game_name)}
          className="w-full flex items-center justify-center gap-2 py-3 bg-emerald-500 hover:bg-emerald-600 text-white font-semibold rounded-xl transition"
          data-testid={`play-btn-${game.game_name}`}
          disabled={!game.is_active}
        >
          <ChevronRight className="w-4 h-4" />
          {game.is_active ? 'Deposit & Play' : 'Currently Unavailable'}
        </button>
      </div>
    </div>
  );
};

export default PublicGames;

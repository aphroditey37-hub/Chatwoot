import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Gamepad2, Download, Search, Star, ChevronLeft, ChevronRight,
  CheckCircle, Smartphone, Monitor, Globe, Sparkles, Play
} from 'lucide-react';

// Centralized API
import { gamesApi } from '../api/endpoints';
import http from '../api/http';

const PublicGamesPage = () => {
  const navigate = useNavigate();
  const [games, setGames] = useState([]);
  const [heroSlides, setHeroSlides] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [currentSlide, setCurrentSlide] = useState(0);

  const fetchData = useCallback(async () => {
    try {
      const [gamesRes, slidesRes] = await Promise.all([
        gamesApi.getPublicGames(),
        http.get('/public/hero-slides').catch(() => ({ data: { slides: [] } }))
      ]);
      
      setGames(gamesRes.data.games || gamesRes.data || []);
      
      if (slidesRes.data?.slides?.length > 0) {
        setHeroSlides(slidesRes.data.slides);
      } else {
        setHeroSlides(getDefaultSlides());
      }
    } catch (error) {
      console.error('Failed to fetch data:', error);
      setHeroSlides(getDefaultSlides());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Auto-advance hero slider
  useEffect(() => {
    if (heroSlides.length > 1) {
      const timer = setInterval(() => {
        setCurrentSlide((prev) => (prev + 1) % heroSlides.length);
      }, 5000);
      return () => clearInterval(timer);
    }
  }, [heroSlides.length]);

  const getDefaultSlides = () => [
    {
      slide_id: '1',
      title: 'Welcome to Gaming Hub',
      description: 'Download your favorite games and start playing today',
      image_url: 'https://images.unsplash.com/photo-1538481199705-c710c4e965fc?w=1200',
      link_url: null
    },
    {
      slide_id: '2',
      title: 'New Games Available',
      description: 'Check out our latest collection of exciting games',
      image_url: 'https://images.unsplash.com/photo-1511512578047-dfb367046420?w=1200',
      link_url: null
    },
    {
      slide_id: '3',
      title: 'Play Anywhere',
      description: 'Available on Android, iOS, and PC platforms',
      image_url: 'https://images.unsplash.com/photo-1552820728-8b83bb6b2b0c?w=1200',
      link_url: null
    }
  ];

  const filteredGames = games.filter(game => 
    game.display_name?.toLowerCase().includes(search.toLowerCase()) ||
    game.game_name?.toLowerCase().includes(search.toLowerCase())
  );

  const nextSlide = () => setCurrentSlide((prev) => (prev + 1) % heroSlides.length);
  const prevSlide = () => setCurrentSlide((prev) => (prev - 1 + heroSlides.length) % heroSlides.length);

  return (
    <div className="min-h-screen bg-[#0a0a0f]" data-testid="public-games-page">
      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-[#0a0a0f]/90 backdrop-blur-xl border-b border-white/5">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-violet-500 to-fuchsia-500 rounded-xl flex items-center justify-center">
              <Gamepad2 className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold text-white">GameHub</span>
          </div>
          <button
            onClick={() => navigate('/login')}
            className="px-5 py-2.5 bg-white/10 hover:bg-white/15 text-white text-sm font-medium rounded-xl transition-all"
            data-testid="login-btn"
          >
            Sign In
          </button>
        </div>
      </header>

      {/* Hero Slider */}
      <section className="pt-20 relative overflow-hidden">
        <div className="relative h-[400px] md:h-[500px]">
          {heroSlides.map((slide, index) => (
            <div
              key={slide.slide_id}
              className={`absolute inset-0 transition-opacity duration-700 ${
                index === currentSlide ? 'opacity-100' : 'opacity-0 pointer-events-none'
              }`}
            >
              {/* Background Image */}
              <div 
                className="absolute inset-0 bg-cover bg-center"
                style={{ 
                  backgroundImage: `url(${slide.image_url})`,
                }}
              />
              {/* Gradient Overlay */}
              <div className="absolute inset-0 bg-gradient-to-t from-[#0a0a0f] via-[#0a0a0f]/60 to-transparent" />
              <div className="absolute inset-0 bg-gradient-to-r from-[#0a0a0f]/80 to-transparent" />
              
              {/* Content */}
              <div className="absolute inset-0 flex items-center">
                <div className="max-w-7xl mx-auto px-4 w-full">
                  <div className="max-w-xl">
                    <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-4 leading-tight">
                      {slide.title}
                    </h1>
                    <p className="text-lg text-gray-300 mb-8">
                      {slide.description}
                    </p>
                    <div className="flex gap-4">
                      <button
                        onClick={() => document.getElementById('games-grid').scrollIntoView({ behavior: 'smooth' })}
                        className="px-6 py-3 bg-gradient-to-r from-violet-600 to-fuchsia-600 hover:from-violet-500 hover:to-fuchsia-500 text-white font-semibold rounded-xl flex items-center gap-2 transition-all shadow-lg shadow-violet-500/25"
                        data-testid="browse-games-btn"
                      >
                        <Play className="w-5 h-5" />
                        Browse Games
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))}

          {/* Slider Controls */}
          {heroSlides.length > 1 && (
            <>
              <button
                onClick={prevSlide}
                className="absolute left-4 top-1/2 -translate-y-1/2 w-12 h-12 bg-black/30 hover:bg-black/50 backdrop-blur rounded-full flex items-center justify-center text-white transition-all"
              >
                <ChevronLeft className="w-6 h-6" />
              </button>
              <button
                onClick={nextSlide}
                className="absolute right-4 top-1/2 -translate-y-1/2 w-12 h-12 bg-black/30 hover:bg-black/50 backdrop-blur rounded-full flex items-center justify-center text-white transition-all"
              >
                <ChevronRight className="w-6 h-6" />
              </button>
              
              {/* Dots */}
              <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex gap-2">
                {heroSlides.map((_, index) => (
                  <button
                    key={index}
                    onClick={() => setCurrentSlide(index)}
                    className={`w-2 h-2 rounded-full transition-all ${
                      index === currentSlide 
                        ? 'w-8 bg-violet-500' 
                        : 'bg-white/30 hover:bg-white/50'
                    }`}
                  />
                ))}
              </div>
            </>
          )}
        </div>
      </section>

      {/* Search Section */}
      <section className="py-8 border-b border-white/5">
        <div className="max-w-7xl mx-auto px-4">
          <div className="relative max-w-md mx-auto">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search games..."
              className="w-full pl-12 pr-4 py-3.5 bg-white/5 border border-white/10 rounded-2xl text-white placeholder-gray-500 focus:outline-none focus:border-violet-500/50 focus:ring-2 focus:ring-violet-500/20 transition-all"
              data-testid="games-search-input"
            />
          </div>
        </div>
      </section>

      {/* Games Grid */}
      <section id="games-grid" className="py-12">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex items-center justify-between mb-8">
            <div>
              <h2 className="text-2xl font-bold text-white mb-1">Available Games</h2>
              <p className="text-gray-500">{filteredGames.length} games available for download</p>
            </div>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-20">
              <div className="w-10 h-10 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : filteredGames.length === 0 ? (
            <div className="text-center py-20">
              <Gamepad2 className="w-16 h-16 text-gray-700 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-white mb-2">No games found</h3>
              <p className="text-gray-500">Try adjusting your search</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {filteredGames.map(game => (
                <GameDownloadCard key={game.game_id} game={game} />
              ))}
            </div>
          )}
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/5 py-12 mt-12">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-violet-500 to-fuchsia-500 rounded-xl flex items-center justify-center">
                <Gamepad2 className="w-5 h-5 text-white" />
              </div>
              <span className="text-lg font-bold text-white">GameHub</span>
            </div>
            <p className="text-gray-500 text-sm">
              © 2024 Gaming Platform. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
};

// Game Download Card Component
const GameDownloadCard = ({ game }) => {
  const [expanded, setExpanded] = useState(false);
  
  const platforms = game.platforms || ['android', 'ios', 'pc'];
  const downloadLinks = game.download_links || {};

  return (
    <div 
      className="group bg-white/[0.02] border border-white/5 rounded-2xl overflow-hidden hover:border-violet-500/30 hover:bg-white/[0.04] transition-all duration-300"
      data-testid={`game-card-${game.game_name}`}
    >
      {/* Game Thumbnail */}
      <div className="relative h-44 bg-gradient-to-br from-violet-900/20 to-fuchsia-900/20 flex items-center justify-center overflow-hidden">
        {game.thumbnail ? (
          <img src={game.thumbnail} alt={game.display_name} className="w-full h-full object-cover" />
        ) : (
          <Gamepad2 className="w-16 h-16 text-violet-500/30" />
        )}
        
        {/* Status Badge */}
        <div className={`absolute top-3 right-3 flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
          game.is_active 
            ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
            : 'bg-red-500/20 text-red-400 border border-red-500/30'
        }`}>
          <CheckCircle className="w-3 h-3" />
          {game.is_active ? 'Available' : 'Unavailable'}
        </div>
        
        {/* Hover Overlay */}
        <div className="absolute inset-0 bg-gradient-to-t from-[#0a0a0f] via-transparent to-transparent opacity-60" />
      </div>

      {/* Content */}
      <div className="p-5">
        <h3 className="text-lg font-bold text-white mb-1 group-hover:text-violet-300 transition-colors">
          {game.display_name}
        </h3>
        <p className="text-gray-500 text-sm mb-4 line-clamp-2">
          {game.description || `Play ${game.display_name} on your favorite device`}
        </p>

        {/* Platform Icons */}
        <div className="flex items-center gap-3 mb-4">
          {platforms.includes('android') && (
            <div className="flex items-center gap-1.5 text-xs text-gray-400">
              <Smartphone className="w-4 h-4" />
              <span>Android</span>
            </div>
          )}
          {platforms.includes('ios') && (
            <div className="flex items-center gap-1.5 text-xs text-gray-400">
              <Smartphone className="w-4 h-4" />
              <span>iOS</span>
            </div>
          )}
          {platforms.includes('pc') && (
            <div className="flex items-center gap-1.5 text-xs text-gray-400">
              <Monitor className="w-4 h-4" />
              <span>PC</span>
            </div>
          )}
        </div>

        {/* Download Button */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full py-3 bg-gradient-to-r from-violet-600 to-fuchsia-600 hover:from-violet-500 hover:to-fuchsia-500 text-white font-semibold rounded-xl flex items-center justify-center gap-2 transition-all shadow-lg shadow-violet-500/20"
          data-testid={`download-btn-${game.game_name}`}
          disabled={!game.is_active}
        >
          <Download className="w-4 h-4" />
          {expanded ? 'Hide Downloads' : 'Download'}
        </button>

        {/* Expanded Download Links */}
        {expanded && game.is_active && (
          <div className="mt-4 space-y-2 animate-fadeIn">
            {platforms.map(platform => (
              <a
                key={platform}
                href={downloadLinks[platform] || '#'}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-between p-3 bg-white/5 hover:bg-white/10 rounded-xl text-sm transition-colors"
              >
                <div className="flex items-center gap-2 text-gray-300">
                  {platform === 'pc' ? <Monitor className="w-4 h-4" /> : <Smartphone className="w-4 h-4" />}
                  <span className="capitalize">{platform}</span>
                </div>
                <Download className="w-4 h-4 text-violet-400" />
              </a>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default PublicGamesPage;

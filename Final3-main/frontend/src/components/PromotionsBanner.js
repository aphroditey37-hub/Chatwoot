/**
 * PromotionsBanner Component
 * Displays active promotions as a slider/carousel on client home
 * Backend-driven content - no hardcoded promotions
 */
import React, { useState, useEffect, useCallback } from 'react';
import { ChevronLeft, ChevronRight, ExternalLink, Sparkles, Gift, Zap } from 'lucide-react';
import { promotionsApi } from '../api/admin';

const PromotionsBanner = () => {
  const [promotions, setPromotions] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(true);

  const fetchPromotions = useCallback(async () => {
    try {
      const res = await promotionsApi.getActive();
      setPromotions(res.data.promotions || []);
      // Track view for first promotion
      if (res.data.promotions?.length > 0) {
        promotionsApi.trackView(res.data.promotions[0].promo_id).catch(() => {});
      }
    } catch (err) {
      console.log('No active promotions');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPromotions();
  }, [fetchPromotions]);

  // Auto-rotate
  useEffect(() => {
    if (promotions.length <= 1) return;
    const timer = setInterval(() => {
      setCurrentIndex((prev) => {
        const next = (prev + 1) % promotions.length;
        // Track view
        promotionsApi.trackView(promotions[next].promo_id).catch(() => {});
        return next;
      });
    }, 5000);
    return () => clearInterval(timer);
  }, [promotions]);

  const goNext = () => {
    const next = (currentIndex + 1) % promotions.length;
    setCurrentIndex(next);
    promotionsApi.trackView(promotions[next].promo_id).catch(() => {});
  };

  const goPrev = () => {
    const prev = (currentIndex - 1 + promotions.length) % promotions.length;
    setCurrentIndex(prev);
    promotionsApi.trackView(promotions[prev].promo_id).catch(() => {});
  };

  const handleClick = (promo) => {
    promotionsApi.trackClick(promo.promo_id).catch(() => {});
    if (promo.cta_link) {
      window.open(promo.cta_link, '_blank');
    }
  };

  // Don't render if no promotions
  if (loading || promotions.length === 0) {
    return null;
  }

  const currentPromo = promotions[currentIndex];
  const bgColor = currentPromo.background_color || '#8b5cf6';
  const textColor = currentPromo.text_color || '#ffffff';

  return (
    <div 
      className="relative rounded-2xl overflow-hidden mb-6 group"
      data-testid="promotions-banner"
      style={{ backgroundColor: bgColor }}
    >
      {/* Background pattern */}
      <div className="absolute inset-0 opacity-10">
        <div className="absolute top-0 left-0 w-40 h-40 bg-white rounded-full blur-3xl transform -translate-x-1/2 -translate-y-1/2"></div>
        <div className="absolute bottom-0 right-0 w-60 h-60 bg-white rounded-full blur-3xl transform translate-x-1/2 translate-y-1/2"></div>
      </div>
      
      <div className="relative px-6 py-5 flex items-center justify-between min-h-[120px]">
        {/* Left content */}
        <div className="flex items-center gap-4 flex-1">
          {/* Icon */}
          <div className="p-3 bg-white/20 rounded-xl backdrop-blur-sm">
            {currentPromo.badge_text?.toLowerCase().includes('bonus') ? (
              <Gift className="w-8 h-8" style={{ color: textColor }} />
            ) : currentPromo.badge_text?.toLowerCase().includes('new') ? (
              <Sparkles className="w-8 h-8" style={{ color: textColor }} />
            ) : (
              <Zap className="w-8 h-8" style={{ color: textColor }} />
            )}
          </div>
          
          {/* Text content */}
          <div className="flex-1">
            {currentPromo.badge_text && (
              <span 
                className="inline-block px-2 py-0.5 text-xs font-bold rounded-full mb-1"
                style={{ backgroundColor: `${textColor}20`, color: textColor }}
              >
                {currentPromo.badge_text}
              </span>
            )}
            <h3 
              className="text-xl font-bold mb-1" 
              style={{ color: textColor }}
            >
              {currentPromo.title}
            </h3>
            {currentPromo.subtitle && (
              <p 
                className="text-sm opacity-80"
                style={{ color: textColor }}
              >
                {currentPromo.subtitle}
              </p>
            )}
          </div>
        </div>
        
        {/* CTA Button */}
        {currentPromo.cta_text && (
          <button
            onClick={() => handleClick(currentPromo)}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold transition-all hover:scale-105"
            style={{ 
              backgroundColor: textColor, 
              color: bgColor 
            }}
            data-testid="promo-cta-btn"
          >
            {currentPromo.cta_text}
            <ExternalLink className="w-4 h-4" />
          </button>
        )}
        
        {/* Navigation arrows (show on hover if multiple) */}
        {promotions.length > 1 && (
          <>
            <button
              onClick={goPrev}
              className="absolute left-2 top-1/2 -translate-y-1/2 p-1.5 rounded-full bg-black/20 hover:bg-black/40 transition opacity-0 group-hover:opacity-100"
              style={{ color: textColor }}
              data-testid="promo-prev-btn"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <button
              onClick={goNext}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-full bg-black/20 hover:bg-black/40 transition opacity-0 group-hover:opacity-100"
              style={{ color: textColor }}
              data-testid="promo-next-btn"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          </>
        )}
      </div>
      
      {/* Dots indicator */}
      {promotions.length > 1 && (
        <div className="absolute bottom-2 left-1/2 -translate-x-1/2 flex gap-1.5">
          {promotions.map((_, idx) => (
            <button
              key={idx}
              onClick={() => {
                setCurrentIndex(idx);
                promotionsApi.trackView(promotions[idx].promo_id).catch(() => {});
              }}
              className={`w-2 h-2 rounded-full transition-all ${
                idx === currentIndex 
                  ? 'w-4 bg-white' 
                  : 'bg-white/40 hover:bg-white/60'
              }`}
              data-testid={`promo-dot-${idx}`}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default PromotionsBanner;

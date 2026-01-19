"""
Public APIs - No authentication required
For public games site and hero slider
"""
from fastapi import APIRouter
from typing import List, Dict, Any
from ..core.database import get_pool

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/games")
async def get_public_games():
    """
    Get games list for public site (no auth required)
    Returns download links only, no wallet/recharge actions
    """
    pool = await get_pool()
    
    async with pool.acquire() as conn:
        games = await conn.fetch("""
            SELECT 
                game_id,
                game_name,
                display_name,
                description,
                thumbnail,
                category,
                is_active
            FROM games
            WHERE is_active = TRUE
            ORDER BY display_name
        """)
        
        return {
            "success": True,
            "games": [
                {
                    **dict(game),
                    "platforms": ["android", "ios", "pc"],
                    "download_links": {
                        "android": f"https://download.example.com/{game['game_name']}/android",
                        "ios": f"https://download.example.com/{game['game_name']}/ios",
                        "pc": f"https://download.example.com/{game['game_name']}/pc"
                    }
                }
                for game in games
            ]
        }


@router.get("/hero-slides")
async def get_hero_slides():
    """
    Get hero slides for public games site
    Returns active slides ordered by display_order
    """
    pool = await get_pool()
    
    async with pool.acquire() as conn:
        # Check if hero_slides table exists
        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'hero_slides'
            )
        """)
        
        if not table_exists:
            return {"success": True, "slides": []}
        
        slides = await conn.fetch("""
            SELECT 
                slide_id,
                title,
                description,
                image_url,
                link_url,
                display_order
            FROM hero_slides
            WHERE is_active = TRUE
            ORDER BY display_order ASC
        """)
        
        return {
            "success": True,
            "slides": [dict(slide) for slide in slides]
        }


@router.get("/games/{game_id}")
async def get_public_game_detail(game_id: str):
    """Get single game details for public site"""
    pool = await get_pool()
    
    async with pool.acquire() as conn:
        game = await conn.fetchrow("""
            SELECT 
                game_id,
                game_name,
                display_name,
                description,
                thumbnail,
                category,
                is_active
            FROM games
            WHERE game_id = $1 AND is_active = TRUE
        """, game_id)
        
        if not game:
            return {"success": False, "error": "Game not found"}
        
        return {
            "success": True,
            "game": {
                **dict(game),
                "platforms": ["android", "ios", "pc"],
                "download_links": {
                    "android": f"https://download.example.com/{game['game_name']}/android",
                    "ios": f"https://download.example.com/{game['game_name']}/ios",
                    "pc": f"https://download.example.com/{game['game_name']}/pc"
                },
                "features": [
                    "HD Graphics",
                    "Multiplayer Support",
                    "Regular Updates",
                    "24/7 Support"
                ]
            }
        }

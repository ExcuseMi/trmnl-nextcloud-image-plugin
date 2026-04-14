import logging
import time

import aiohttp
from modules.utils.state import get_pool

log = logging.getLogger(__name__)

GEOCODE_TTL = 30 * 24 * 3600  # 30 days — towns don't move


def _key(lat: float, lon: float) -> str:
    """Round to 2 decimal places (~1.1 km grid) so nearby photos share a cache entry."""
    return f"{lat:.2f},{lon:.2f}"


async def reverse_geocode(lat: float, lon: float) -> str | None:
    key = _key(lat, lon)

    # --- cache read ---
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT location, cached_at FROM geocode_cache WHERE key = $1", key
            )
            if row:
                location, cached_at = row['location'], row['cached_at']
                if time.time() - cached_at < GEOCODE_TTL:
                    return location or None  # None means "no result" — don't retry until TTL
    except Exception as exc:
        log.warning('Geocode cache read failed: %s', exc)

    # --- Nominatim lookup ---
    location = None
    try:
        url = (
            f"https://nominatim.openstreetmap.org/reverse"
            f"?lat={lat}&lon={lon}&format=json&zoom=10"
        )
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers={'User-Agent': 'TRMNL-Nextcloud-Plugin/1.0 (self-hosted)'},
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    addr = data.get('address', {})
                    # Prioritize common town/city fields
                    location = (
                        addr.get('city')
                        or addr.get('town')
                        or addr.get('village')
                        or addr.get('municipality')
                        or addr.get('county')
                        or addr.get('state')
                        or addr.get('country')
                    )
    except Exception as exc:
        log.warning('Nominatim lookup failed for %.4f,%.4f: %s', lat, lon, exc)

    # --- cache write (store None too, to suppress future retries until TTL) ---
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO geocode_cache (key, location, cached_at) VALUES ($1, $2, $3) "
                "ON CONFLICT (key) DO UPDATE SET location = EXCLUDED.location, cached_at = EXCLUDED.cached_at",
                key, location, int(time.time()),
            )
    except Exception as exc:
        log.warning('Geocode cache write failed: %s', exc)

    return location

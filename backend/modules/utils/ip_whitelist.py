import asyncio
import logging
import os
from functools import wraps

import aiohttp
from quart import jsonify, request

TRMNL_IPS_API = 'https://trmnl.com/api/ips'
ENABLE_IP_WHITELIST = os.getenv('ENABLE_IP_WHITELIST', 'true').lower() == 'true'
IP_REFRESH_HOURS = int(os.getenv('IP_REFRESH_HOURS', '24'))
LOCALHOST_IPS = {'127.0.0.1', '::1'}

log = logging.getLogger(__name__)
_ips: set[str] = set(LOCALHOST_IPS)
_lock = asyncio.Lock()


async def _fetch_ips() -> set[str]:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(TRMNL_IPS_API, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                resp.raise_for_status()
                data = await resp.json()
                addrs = data.get('data', {})
                ips = set(addrs.get('ipv4', []) + addrs.get('ipv6', [])) | LOCALHOST_IPS
                log.info('Loaded %d TRMNL IPs', len(ips))
                return ips
    except Exception as exc:
        log.warning('Failed to fetch TRMNL IPs: %s', exc)
        return set()


async def _refresh_loop():
    while True:
        await asyncio.sleep(IP_REFRESH_HOURS * 3600)
        fresh = await _fetch_ips()
        if fresh:
            async with _lock:
                global _ips
                _ips = fresh


async def init_ip_whitelist():
    global _ips
    if not ENABLE_IP_WHITELIST:
        log.info('IP whitelist disabled')
        return
    fresh = await _fetch_ips()
    if fresh:
        async with _lock:
            _ips = fresh
    asyncio.create_task(_refresh_loop())
    log.info('IP whitelist enabled — refresh every %dh', IP_REFRESH_HOURS)


def _client_ip() -> str:
    for header in ('CF-Connecting-IP', 'X-Forwarded-For', 'X-Real-IP'):
        value = request.headers.get(header)
        if value:
            return value.split(',')[0].strip()
    return request.remote_addr


def require_trmnl_ip(f):
    @wraps(f)
    async def decorated(*args, **kwargs):
        if not ENABLE_IP_WHITELIST:
            return await f(*args, **kwargs)
        ip = _client_ip()
        async with _lock:
            allowed = ip in _ips
        if not allowed:
            log.warning('Blocked request from %s', ip)
            return jsonify({'error': 'Access denied'}), 403
        return await f(*args, **kwargs)
    return decorated

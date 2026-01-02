/**
 * PyCraft CurseForge API Proxy
 *
 * This Worker acts as a proxy between PyCraft and the CurseForge API,
 * keeping the API key secure on Cloudflare's servers.
 *
 * Features:
 * - API key protection
 * - Rate limiting (per IP and global)
 * - Whitelist of allowed endpoints
 */

const CURSEFORGE_API_BASE = 'https://api.curseforge.com';
const MINECRAFT_GAME_ID = '432';
const MODPACK_CLASS_ID = '4471';

// Rate limit configuration
const RATE_LIMITS = {
  perIpPerMinute: 600,      // Allows fast modpack installation
  perIpPerDay: 5000,        // Prevents individual abuse
  globalPerDay: 85000,      // Protects CurseForge API limit (100k)
};

// Allowed endpoints (whitelist for security)
const ALLOWED_PATHS = [
  '/v1/mods/search',
  '/v1/mods',
  '/v1/categories',
];

// Helper: Get current minute key (for per-minute rate limiting)
function getMinuteKey(ip) {
  const now = new Date();
  const minute = `${now.getUTCFullYear()}-${now.getUTCMonth() + 1}-${now.getUTCDate()}-${now.getUTCHours()}-${now.getUTCMinutes()}`;
  return `ip:${ip}:min:${minute}`;
}

// Helper: Get current day key (for per-day rate limiting)
function getDayKey(ip) {
  const now = new Date();
  const day = `${now.getUTCFullYear()}-${now.getUTCMonth() + 1}-${now.getUTCDate()}`;
  return `ip:${ip}:day:${day}`;
}

// Helper: Get global day key
function getGlobalDayKey() {
  const now = new Date();
  const day = `${now.getUTCFullYear()}-${now.getUTCMonth() + 1}-${now.getUTCDate()}`;
  return `global:day:${day}`;
}

// Check and update rate limits
async function checkRateLimit(ip, kv) {
  const minuteKey = getMinuteKey(ip);
  const dayKey = getDayKey(ip);
  const globalKey = getGlobalDayKey();

  // Get current counts
  const [minuteCount, dayCount, globalCount] = await Promise.all([
    kv.get(minuteKey).then(v => parseInt(v) || 0),
    kv.get(dayKey).then(v => parseInt(v) || 0),
    kv.get(globalKey).then(v => parseInt(v) || 0),
  ]);

  // Check limits
  if (minuteCount >= RATE_LIMITS.perIpPerMinute) {
    return {
      allowed: false,
      error: 'Rate limit exceeded (per minute). Please wait a moment.',
      retryAfter: 60,
    };
  }

  if (dayCount >= RATE_LIMITS.perIpPerDay) {
    return {
      allowed: false,
      error: 'Daily rate limit exceeded. Please try again tomorrow.',
      retryAfter: 3600,
    };
  }

  if (globalCount >= RATE_LIMITS.globalPerDay) {
    return {
      allowed: false,
      error: 'Service is temporarily busy. Please try again later.',
      retryAfter: 3600,
    };
  }

  // Increment counters (fire and forget for performance)
  await Promise.all([
    kv.put(minuteKey, String(minuteCount + 1), { expirationTtl: 120 }),      // Expire after 2 min
    kv.put(dayKey, String(dayCount + 1), { expirationTtl: 86400 }),          // Expire after 24h
    kv.put(globalKey, String(globalCount + 1), { expirationTtl: 86400 }),    // Expire after 24h
  ]);

  return {
    allowed: true,
    remaining: {
      minute: RATE_LIMITS.perIpPerMinute - minuteCount - 1,
      day: RATE_LIMITS.perIpPerDay - dayCount - 1,
      global: RATE_LIMITS.globalPerDay - globalCount - 1,
    },
  };
}

function isAllowedPath(pathname) {
  return ALLOWED_PATHS.some(allowed => pathname.startsWith(allowed));
}

function validateSearchParams(url) {
  if (url.pathname === '/v1/mods/search') {
    const gameId = url.searchParams.get('gameId');
    const classId = url.searchParams.get('classId');

    if (gameId !== MINECRAFT_GAME_ID) {
      return { valid: false, error: 'Only Minecraft (gameId=432) is allowed' };
    }
    if (classId !== MODPACK_CLASS_ID) {
      return { valid: false, error: 'Only Modpacks (classId=4471) are allowed' };
    }
  }

  return { valid: true };
}

// Get client IP from request
function getClientIP(request) {
  return request.headers.get('CF-Connecting-IP') ||
         request.headers.get('X-Forwarded-For')?.split(',')[0]?.trim() ||
         'unknown';
}

export default {
  async fetch(request, env) {
    // Handle CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type',
          'Access-Control-Max-Age': '86400',
        },
      });
    }

    // Only allow GET and POST
    if (!['GET', 'POST'].includes(request.method)) {
      return new Response(JSON.stringify({ error: 'Method not allowed' }), {
        status: 405,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Verify API key is configured
    const apiKey = env.CURSEFORGE_API_KEY;
    if (!apiKey) {
      return new Response(JSON.stringify({ error: 'API Key not configured' }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const url = new URL(request.url);
    const pathname = url.pathname;

    // Verify path is allowed
    if (!isAllowedPath(pathname)) {
      return new Response(JSON.stringify({ error: 'Path not allowed' }), {
        status: 403,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Validate search parameters
    const validation = validateSearchParams(url);
    if (!validation.valid) {
      return new Response(JSON.stringify({ error: validation.error }), {
        status: 400,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
        },
      });
    }

    // Check rate limits
    const clientIP = getClientIP(request);
    const rateLimit = await checkRateLimit(clientIP, env.RATE_LIMIT);

    if (!rateLimit.allowed) {
      return new Response(JSON.stringify({
        error: rateLimit.error,
        retryAfter: rateLimit.retryAfter,
      }), {
        status: 429,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
          'Retry-After': String(rateLimit.retryAfter),
        },
      });
    }

    // Build target URL
    const targetUrl = `${CURSEFORGE_API_BASE}${pathname}${url.search}`;

    try {
      // Prepare headers for CurseForge
      const headers = {
        'Accept': 'application/json',
        'x-api-key': apiKey,
      };

      // Prepare body if POST
      let body = null;
      if (request.method === 'POST') {
        headers['Content-Type'] = 'application/json';
        body = await request.text();
      }

      // Make request to CurseForge
      const response = await fetch(targetUrl, {
        method: request.method,
        headers: headers,
        body: body,
      });

      // Get response
      const data = await response.text();

      // Return with CORS headers and rate limit info
      return new Response(data, {
        status: response.status,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
          'Cache-Control': 'public, max-age=300',
          'X-RateLimit-Remaining-Minute': String(rateLimit.remaining.minute),
          'X-RateLimit-Remaining-Day': String(rateLimit.remaining.day),
        },
      });

    } catch (error) {
      return new Response(JSON.stringify({
        error: 'Proxy error',
        message: error.message
      }), {
        status: 500,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
        },
      });
    }
  },
};

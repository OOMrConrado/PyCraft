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

// Rate limit configuration.
// Tuned for heavy but legitimate PyCraft usage:
//   A 400-mod modpack install uses ~40 batch calls + ~400 file-info calls (~440/install).
//   Power users testing ~10 modpacks/day stay well under 30k/day.
// The global cap protects the CurseForge API key's 100k/day ceiling.
const RATE_LIMITS = {
  perIpPerMinute: 1000,     // Burst-friendly for parallel downloaders
  perIpPerDay: 30000,       // Generous for heavy testers, still caps abuse at ~35% of global
  globalPerDay: 85000,      // Protects CurseForge API limit (100k/day) with 15% safety margin
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

// Check rate limits and return current counts. The caller is responsible for
// scheduling the increment writes via ctx.waitUntil so they don't block the response.
async function checkRateLimit(ip, kv) {
  const minuteKey = getMinuteKey(ip);
  const dayKey = getDayKey(ip);
  const globalKey = getGlobalDayKey();

  const [minuteCount, dayCount, globalCount] = await Promise.all([
    kv.get(minuteKey).then(v => parseInt(v) || 0),
    kv.get(dayKey).then(v => parseInt(v) || 0),
    kv.get(globalKey).then(v => parseInt(v) || 0),
  ]);

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

  return {
    allowed: true,
    counts: { minuteCount, dayCount, globalCount },
    keys: { minuteKey, dayKey, globalKey },
    remaining: {
      minute: RATE_LIMITS.perIpPerMinute - minuteCount - 1,
      day: RATE_LIMITS.perIpPerDay - dayCount - 1,
      global: RATE_LIMITS.globalPerDay - globalCount - 1,
    },
  };
}

// Schedule the counter increments after the response is sent.
function scheduleIncrement(ctx, kv, rateLimit) {
  const { keys, counts } = rateLimit;
  ctx.waitUntil(Promise.all([
    kv.put(keys.minuteKey, String(counts.minuteCount + 1), { expirationTtl: 120 }),
    kv.put(keys.dayKey, String(counts.dayCount + 1), { expirationTtl: 86400 }),
    kv.put(keys.globalKey, String(counts.globalCount + 1), { expirationTtl: 86400 }),
  ]));
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

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, User-Agent',
  'Access-Control-Max-Age': '86400',
};

function jsonResponse(body, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      'Content-Type': 'application/json',
      ...CORS_HEADERS,
      ...extraHeaders,
    },
  });
}

export default {
  async fetch(request, env, ctx) {
    // CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: CORS_HEADERS });
    }

    const url = new URL(request.url);
    const pathname = url.pathname;

    // Public health endpoint — no auth, no rate limit, useful for monitoring.
    if (pathname === '/health' || pathname === '/') {
      return jsonResponse({
        status: 'ok',
        service: 'pycraft-curseforge-proxy',
        limits: {
          perIpPerMinute: RATE_LIMITS.perIpPerMinute,
          perIpPerDay: RATE_LIMITS.perIpPerDay,
        },
      }, 200, { 'Cache-Control': 'public, max-age=60' });
    }

    if (!['GET', 'POST'].includes(request.method)) {
      return jsonResponse({ error: 'Method not allowed' }, 405);
    }

    // Soft User-Agent gate — enable by setting REQUIRE_PYCRAFT_UA="1" in the worker env.
    // This is light protection: trivial to forge, but blocks casual scrapers that find the URL.
    if (env.REQUIRE_PYCRAFT_UA === '1') {
      const ua = request.headers.get('User-Agent') || '';
      if (!ua.toLowerCase().includes('pycraft')) {
        return jsonResponse({ error: 'Forbidden' }, 403);
      }
    }

    // Verify API key is configured (server-side misconfiguration — generic message)
    const apiKey = env.CURSEFORGE_API_KEY;
    if (!apiKey) {
      return jsonResponse({ error: 'Service unavailable' }, 503);
    }

    if (!isAllowedPath(pathname)) {
      return jsonResponse({ error: 'Path not allowed' }, 403);
    }

    const validation = validateSearchParams(url);
    if (!validation.valid) {
      return jsonResponse({ error: validation.error }, 400);
    }

    const clientIP = getClientIP(request);
    const rateLimit = await checkRateLimit(clientIP, env.RATE_LIMIT);

    if (!rateLimit.allowed) {
      return jsonResponse(
        { error: rateLimit.error, retryAfter: rateLimit.retryAfter },
        429,
        { 'Retry-After': String(rateLimit.retryAfter) },
      );
    }

    const targetUrl = `${CURSEFORGE_API_BASE}${pathname}${url.search}`;

    try {
      const headers = {
        'Accept': 'application/json',
        'x-api-key': apiKey,
      };

      let body = null;
      if (request.method === 'POST') {
        headers['Content-Type'] = 'application/json';
        body = await request.text();
      }

      const response = await fetch(targetUrl, {
        method: request.method,
        headers,
        body,
      });

      const data = await response.text();

      // Only count successful upstream calls against the budget — failures from
      // CurseForge shouldn't punish the user.
      if (response.ok) {
        scheduleIncrement(ctx, env.RATE_LIMIT, rateLimit);
      }

      return new Response(data, {
        status: response.status,
        headers: {
          'Content-Type': 'application/json',
          ...CORS_HEADERS,
          'Cache-Control': 'public, max-age=300',
          'X-RateLimit-Remaining-Minute': String(rateLimit.remaining.minute),
          'X-RateLimit-Remaining-Day': String(rateLimit.remaining.day),
        },
      });

    } catch (error) {
      // Don't leak internal error details to clients.
      console.error('Upstream fetch failed:', error);
      return jsonResponse({ error: 'Upstream request failed' }, 502);
    }
  },
};

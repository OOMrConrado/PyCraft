/**
 * PyCraft CurseForge API Proxy
 *
 * This Worker acts as a proxy between PyCraft and the CurseForge API,
 * keeping the API key secure on Cloudflare's servers.
 *
 * IMPORTANT: This proxy only allows modpack-related endpoints (classId=4471)
 * to prevent misuse of the API key.
 */

const CURSEFORGE_API_BASE = 'https://api.curseforge.com';
const MINECRAFT_GAME_ID = '432';
const MODPACK_CLASS_ID = '4471';

// Allowed endpoints (whitelist for security)
const ALLOWED_PATHS = [
  '/v1/mods/search',
  '/v1/mods',
  '/v1/categories',
];

function isAllowedPath(pathname) {
  // Allow paths that start with any of the allowed ones
  // This includes /v1/mods/12345, /v1/mods/12345/files, etc.
  return ALLOWED_PATHS.some(allowed => pathname.startsWith(allowed));
}

function validateSearchParams(url) {
  // For search endpoint, ensure it's searching for modpacks only
  if (url.pathname === '/v1/mods/search') {
    const gameId = url.searchParams.get('gameId');
    const classId = url.searchParams.get('classId');

    // Must be Minecraft (432) and Modpacks (4471)
    if (gameId !== MINECRAFT_GAME_ID) {
      return { valid: false, error: 'Only Minecraft (gameId=432) is allowed' };
    }
    if (classId !== MODPACK_CLASS_ID) {
      return { valid: false, error: 'Only Modpacks (classId=4471) are allowed' };
    }
  }

  return { valid: true };
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

      // Return with CORS headers
      return new Response(data, {
        status: response.status,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
          'Cache-Control': 'public, max-age=300', // Cache 5 minutes
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

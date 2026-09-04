/**
 * Lunch menu sync — Cloudflare Worker.
 *
 * Replaces localStorage-only storage (which never synced across devices)
 * with a shared endpoint any device can read from and write to. No auth
 * token needed client-side since this data isn't sensitive — it's a
 * school lunch menu, not something worth protecting behind credentials.
 *
 * GET  /        -> returns the current stored menu as JSON
 * POST /        -> body is {dateISO: menuText, ...}; overwrites the stored menu
 */

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

export default {
  async fetch(request, env, ctx) {
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: CORS_HEADERS });
    }

    if (request.method === "GET") {
      const stored = await env.LUNCH_KV.get("menu");
      return new Response(stored || "{}", {
        headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
      });
    }

    if (request.method === "POST") {
      try {
        const body = await request.json();
        // Basic sanity check — expects a flat object of dateISO -> string
        if (typeof body !== "object" || body === null || Array.isArray(body)) {
          return new Response(JSON.stringify({ error: "Expected a flat object of date -> menu text" }), {
            status: 400,
            headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
          });
        }
        await env.LUNCH_KV.put("menu", JSON.stringify(body));
        return new Response(JSON.stringify({ ok: true, days: Object.keys(body).length }), {
          headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
        });
      } catch (e) {
        return new Response(JSON.stringify({ error: e.message }), {
          status: 400,
          headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
        });
      }
    }

    return new Response("Method not allowed", { status: 405, headers: CORS_HEADERS });
  },
};

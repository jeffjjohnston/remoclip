/**
 * Cloudflare Worker for serving static MkDocs documentation from R2.
 * - Redirects /latest/ → /vX.Y/ (based on latest-version.txt)
 * - Serves immutable versioned files from R2
 * - Redirects / → /latest/
 * - Custom 404 fallback if 404.html exists
 */

const CACHE_CONTROL_IMMUTABLE = "public, max-age=31536000, immutable";
const CACHE_CONTROL_DYNAMIC = "public, max-age=60, must-revalidate";

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // Redirect the root path to /latest/
    if (url.pathname === "/" || url.pathname === "") {
      return Response.redirect(`https://${url.host}/latest/`, 302);
    }

    // Handle the /latest/ alias (redirect to current version)
    if (url.pathname.startsWith("/latest/")) {
      const latestObj = await env.DOCS_BUCKET.get("latest-version.txt");
      if (!latestObj) {
        return new Response("latest-version.txt not found", { status: 500 });
      }

      const latestVersion = (await latestObj.text()).trim();
      const rewritten = url.pathname.replace(
        /^\/latest\//,
        `/${latestVersion}/`
      );
      return Response.redirect(`https://${url.host}${rewritten}`, 302);
    }

    // Serve static files for versioned paths (e.g. /v1.2/guide/)
    let key = url.pathname.slice(1); // remove leading "/"
    if (url.pathname.endsWith("/")) key += "index.html";
    if (key === "") key = "index.html";

    const obj = await env.DOCS_BUCKET.get(key);
    if (!obj) {
      // Attempt to serve custom 404.html
      const notFoundObj = await env.DOCS_BUCKET.get("404.html");
      if (notFoundObj) {
        const headers = new Headers();
        notFoundObj.writeHttpMetadata(headers);
        headers.set("Cache-Control", "no-store");
        return new Response(notFoundObj.body, { status: 404, headers });
      }
      return new Response("404 Not Found", { status: 404 });
    }

    // Prepare response headers
    const headers = new Headers();
    obj.writeHttpMetadata(headers);
    headers.set("Cache-Control", CACHE_CONTROL_IMMUTABLE);
    headers.set("X-Content-Type-Options", "nosniff");
    headers.set("Referrer-Policy", "same-origin");

    return new Response(obj.body, { headers });
  },
};


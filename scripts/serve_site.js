const fs = require('fs');
const http = require('http');
const https = require('https');
const path = require('path');

const PORT = Number(process.env.PORT || 3000);
const API_TARGET = process.env.API_TARGET || 'http://127.0.0.1:3005';
const STATIC_DIR = path.resolve(
  process.env.STATIC_DIR || path.join(__dirname, '..', 'frontend', 'dist'),
);

const mimeTypes = {
  '.css': 'text/css; charset=utf-8',
  '.gif': 'image/gif',
  '.html': 'text/html; charset=utf-8',
  '.ico': 'image/x-icon',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.js': 'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.map': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.txt': 'text/plain; charset=utf-8',
  '.webp': 'image/webp',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
};

function sendFile(filePath, res, method) {
  fs.stat(filePath, (statError, stats) => {
    if (statError || !stats.isFile()) {
      res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
      res.end('Not Found');
      return;
    }

    const ext = path.extname(filePath).toLowerCase();
    res.writeHead(200, {
      'Content-Type': mimeTypes[ext] || 'application/octet-stream',
      'Content-Length': stats.size,
      'Cache-Control': ext === '.html' ? 'no-cache' : 'public, max-age=31536000, immutable',
    });

    if (method === 'HEAD') {
      res.end();
      return;
    }

    fs.createReadStream(filePath).pipe(res);
  });
}

function proxyRequest(req, res) {
  const targetUrl = new URL(req.url, API_TARGET);
  const transport = targetUrl.protocol === 'https:' ? https : http;

  const proxyReq = transport.request(
    targetUrl,
    {
      method: req.method,
      headers: {
        ...req.headers,
        host: targetUrl.host,
      },
    },
    (proxyRes) => {
      res.writeHead(proxyRes.statusCode || 502, proxyRes.headers);
      proxyRes.pipe(res);
    },
  );

  proxyReq.on('error', (error) => {
    res.writeHead(502, { 'Content-Type': 'application/json; charset=utf-8' });
    res.end(
      JSON.stringify({
        success: false,
        error: {
          message: `Upstream request failed: ${error.message}`,
        },
      }),
    );
  });

  req.pipe(proxyReq);
}

function resolveStaticPath(urlPathname) {
  const decodedPath = decodeURIComponent(urlPathname);
  const normalizedPath = path.normalize(decodedPath).replace(/^(\.\.[/\\])+/, '');
  const candidate = path.join(STATIC_DIR, normalizedPath);

  if (!candidate.startsWith(STATIC_DIR)) {
    return null;
  }

  return candidate;
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://${req.headers.host || '127.0.0.1'}`);
  const { pathname } = url;

  if (pathname.startsWith('/api/') || pathname === '/health') {
    proxyRequest(req, res);
    return;
  }

  const requestedPath =
    pathname === '/' ? path.join(STATIC_DIR, 'index.html') : resolveStaticPath(pathname);

  if (!requestedPath) {
    res.writeHead(403, { 'Content-Type': 'text/plain; charset=utf-8' });
    res.end('Forbidden');
    return;
  }

  fs.stat(requestedPath, (statError, stats) => {
    if (!statError && stats.isFile()) {
      sendFile(requestedPath, res, req.method || 'GET');
      return;
    }

    sendFile(path.join(STATIC_DIR, 'index.html'), res, req.method || 'GET');
  });
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`OpenClaw site gateway listening on port ${PORT}`);
  console.log(`Serving static files from ${STATIC_DIR}`);
  console.log(`Proxying API traffic to ${API_TARGET}`);
});

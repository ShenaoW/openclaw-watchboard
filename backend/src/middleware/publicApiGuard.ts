import type { NextFunction, Request, Response } from 'express';

function getAllowedHosts() {
  const configured = [
    'clawsec.com.cn',
    'www.clawsec.com.cn',
    'localhost',
    '127.0.0.1',
    ...(process.env.FRONTEND_URLS || process.env.FRONTEND_URL || '')
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean)
      .map((value) => {
        try {
          return new URL(value).host;
        } catch {
          return value.replace(/^https?:\/\//, '');
        }
      }),
  ];

  return new Set(configured.filter(Boolean));
}

function extractHost(value?: string) {
  if (!value) {
    return '';
  }

  try {
    return new URL(value).host;
  } catch {
    return '';
  }
}

export function publicApiGuard(req: Request, res: Response, next: NextFunction) {
  if (process.env.NODE_ENV !== 'production') {
    next();
    return;
  }

  const clientHeader = req.get('x-watchboard-client');
  const secFetchSite = req.get('sec-fetch-site');
  const originHost = extractHost(req.get('origin'));
  const refererHost = extractHost(req.get('referer'));
  const hostHeader = req.get('host') || '';
  const allowedHosts = getAllowedHosts();

  const hasAllowedSource =
    allowedHosts.has(originHost) ||
    allowedHosts.has(refererHost) ||
    allowedHosts.has(hostHeader);

  const hasBrowserContext =
    clientHeader === 'web' ||
    secFetchSite === 'same-origin' ||
    secFetchSite === 'same-site';

  if (hasAllowedSource && hasBrowserContext) {
    next();
    return;
  }

  res.status(403).json({
    success: false,
    error: {
      message: 'Forbidden',
      code: 'API_ACCESS_DENIED',
    },
    timestamp: new Date().toISOString(),
  });
}

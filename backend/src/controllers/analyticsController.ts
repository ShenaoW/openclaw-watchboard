import { NextFunction, Request, Response } from 'express';
import { analyticsService } from '../services/AnalyticsService';

function getClientIp(req: Request) {
  const forwardedFor = req.headers['x-forwarded-for'];

  if (typeof forwardedFor === 'string' && forwardedFor.trim()) {
    return forwardedFor.split(',')[0].trim();
  }

  if (Array.isArray(forwardedFor) && forwardedFor.length > 0) {
    return forwardedFor[0].trim();
  }

  return req.ip || req.socket.remoteAddress || 'unknown';
}

export class AnalyticsController {
  async recordPageView(req: Request, res: Response, next: NextFunction) {
    try {
      const pagePath = typeof req.body?.pagePath === 'string' ? req.body.pagePath.trim() : '';

      if (!pagePath || pagePath.startsWith('/api')) {
        res.status(400).json({
          success: false,
          error: {
            message: 'Invalid page path',
            code: 'INVALID_PAGE_PATH',
          },
        });
        return;
      }

      await analyticsService.recordPageView({
        pagePath,
        clientIp: getClientIp(req),
        userAgent: req.get('user-agent'),
        referer: req.get('referer'),
      });

      res.status(204).send();
    } catch (error) {
      next(error);
    }
  }

  async getSummary(_req: Request, res: Response, next: NextFunction) {
    try {
      const summary = await analyticsService.getSummary();
      res.json({ success: true, data: summary });
    } catch (error) {
      next(error);
    }
  }
}

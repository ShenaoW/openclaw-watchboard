import { NextFunction, Request, Response } from 'express';
import { exposureDatabaseService } from '../services/ExposureDatabaseService';

export class ExposureController {
  async getExposureOverview(req: Request, res: Response, next: NextFunction) {
    try {
      const overview = await exposureDatabaseService.getOverview();
      res.json({ success: true, data: overview });
    } catch (error) {
      next(error);
    }
  }

  async getExposedServices(req: Request, res: Response, next: NextFunction) {
    try {
      const result = await exposureDatabaseService.getServices({
        status: req.query.status as string | undefined,
        runtimeStatus: req.query.runtimeStatus as string | undefined,
        chinaScope: req.query.chinaScope as string | undefined,
        versionStatus: req.query.versionStatus as string | undefined,
        country: req.query.country as string | undefined,
        isp: req.query.isp as string | undefined,
        credentialsLeaked: req.query.credentials_leaked as string | undefined,
        search: req.query.search as string | undefined,
        page: Number(req.query.page || 1),
        limit: Number(req.query.limit || 20),
      });

      res.json({ success: true, data: result });
    } catch (error) {
      next(error);
    }
  }

  async getGeographicDistribution(req: Request, res: Response, next: NextFunction) {
    try {
      const geoData = await exposureDatabaseService.getGeographicDistribution();
      res.json({ success: true, data: geoData });
    } catch (error) {
      next(error);
    }
  }

  async getPortDistribution(req: Request, res: Response, next: NextFunction) {
    try {
      const portData = await exposureDatabaseService.getPortDistribution();
      res.json({ success: true, data: portData });
    } catch (error) {
      next(error);
    }
  }

  async getRiskLevelDistribution(req: Request, res: Response, next: NextFunction) {
    try {
      const riskDistribution = await exposureDatabaseService.getRiskLevelDistribution();
      res.json({ success: true, data: riskDistribution });
    } catch (error) {
      next(error);
    }
  }

  async getExposureTrends(req: Request, res: Response, next: NextFunction) {
    try {
      const trends = await exposureDatabaseService.getTrends((req.query.timeRange as string) || '7d');
      res.json({ success: true, data: trends });
    } catch (error) {
      next(error);
    }
  }

  async searchTarget(req: Request, res: Response, next: NextFunction) {
    try {
      const result = await exposureDatabaseService.searchTarget(req.params.target);
      res.json({ success: true, data: result });
    } catch (error) {
      next(error);
    }
  }

  async triggerScan(req: Request, res: Response, next: NextFunction) {
    try {
      const { targets = [], scanType = 'quick' } = req.body;
      res.json({
        success: true,
        message: '扫描任务已创建',
        data: {
          id: `scan-${Date.now()}`,
          targets,
          scanType,
          status: 'queued',
          createdAt: new Date().toISOString(),
        },
      });
    } catch (error) {
      next(error);
    }
  }
}

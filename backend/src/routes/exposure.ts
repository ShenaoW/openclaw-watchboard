import express from 'express';
import { ExposureController } from '../controllers/exposureController';

const router = express.Router();
const exposureController = new ExposureController();

/**
 * OpenClaw 公网暴露情况分析路由
 */

// 获取公网暴露总览数据
router.get('/overview', exposureController.getExposureOverview.bind(exposureController));

// 获取暴露服务列表
router.get('/services', exposureController.getExposedServices.bind(exposureController));

// 获取地理分布数据
router.get('/geography', exposureController.getGeographicDistribution.bind(exposureController));

// 获取端口分布统计
router.get('/ports', exposureController.getPortDistribution.bind(exposureController));

// 获取时间趋势数据
router.get('/trends', exposureController.getExposureTrends.bind(exposureController));

// 搜索特定IP或域名的暴露情况
router.get('/search/:target', exposureController.searchTarget.bind(exposureController));

// 刷新暴露数据扫描
router.post('/scan', exposureController.triggerScan.bind(exposureController));

export default router;

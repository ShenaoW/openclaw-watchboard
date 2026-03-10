import express from 'express';
import { RiskController } from '../controllers/riskController';

const router = express.Router();
const riskController = new RiskController();

/**
 * OpenClaw Top 10 安全风险相关路由
 */

// 获取 Top 10 风险列表
router.get('/top10', riskController.getTop10Risks.bind(riskController));

// 获取特定风险详情
router.get('/:riskId', riskController.getRiskDetail.bind(riskController));

// 获取风险统计信息
router.get('/stats/summary', riskController.getRiskStats.bind(riskController));

// 获取风险趋势数据
router.get('/trends/:timeRange', riskController.getRiskTrends.bind(riskController));

// 刷新风险数据
router.post('/refresh', riskController.refreshRiskData.bind(riskController));

export default router;
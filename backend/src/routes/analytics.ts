import express from 'express';
import { AnalyticsController } from '../controllers/analyticsController';

const router = express.Router();
const analyticsController = new AnalyticsController();

router.get('/summary', analyticsController.getSummary.bind(analyticsController));
router.post('/page-view', analyticsController.recordPageView.bind(analyticsController));

export default router;

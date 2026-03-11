import express from 'express';
import { SkillController } from '../controllers/skillController';

const router = express.Router();
const skillController = new SkillController();

/**
 * Skill 投毒和可信 Skill 库管理路由
 */

// 获取可信 Skill 库列表
router.get('/trusted', skillController.getTrustedSkills.bind(skillController));

// 获取可疑/投毒 Skill 检测结果
router.get('/suspicious', skillController.getSuspiciousSkills.bind(skillController));

// 获取恶意 Skill 检测结果
router.get('/malicious', skillController.getMaliciousSkills.bind(skillController));

// 获取 Skill 安全分析报告
router.get('/analysis/:skillId', skillController.getSkillAnalysis.bind(skillController));

// 获取 Skill 使用统计
router.get('/stats', skillController.getSkillUsageStats.bind(skillController));

// 获取 Skill 使用统计 (legacy endpoint)
router.get('/usage/stats', skillController.getSkillUsageStats.bind(skillController));

// 添加 Skill 到可信列表
router.post('/trusted', skillController.addTrustedSkill.bind(skillController));

// 举报可疑 Skill
router.post('/report', skillController.reportSuspiciousSkill.bind(skillController));

// 验证 Skill 安全性
router.post('/verify', skillController.verifySkill.bind(skillController));

// 获取 Skill 库同步状态
router.get('/sync/status', skillController.getSyncStatus.bind(skillController));

// 触发 Skill 库同步
router.post('/sync', skillController.syncSkillDatabase.bind(skillController));

export default router;

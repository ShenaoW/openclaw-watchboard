// 导出所有类型
export * from './types';

// 常量定义
export const RISK_LEVELS = {
  CRITICAL: 'Critical',
  HIGH: 'High',
  MEDIUM: 'Medium',
  LOW: 'Low'
} as const;

export const SKILL_CATEGORIES = {
  SECURITY: 'Security',
  NETWORK: 'Network',
  UTILITY: 'Utility',
  DEVELOPMENT: 'Development',
  SYSTEM: 'System'
} as const;

export const API_ENDPOINTS = {
  RISKS: '/api/risks',
  EXPOSURE: '/api/exposure',
  SKILLS: '/api/skills'
} as const;
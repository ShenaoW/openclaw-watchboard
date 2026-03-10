// 风险相关类型
export interface Risk {
  id: string;
  title: string;
  description: string;
  severity: 'Critical' | 'High' | 'Medium' | 'Low';
  score: number;
  category: string;
  affectedVersions: string[];
  mitigation: string;
  cveId?: string;
  lastUpdated: string;
}

export interface RiskStats {
  totalRisks: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  resolved: number;
  trending: {
    increase: number;
    decrease: number;
  };
}

// 暴露相关类型
export interface ExposedService {
  id: string;
  ip: string;
  hostname?: string;
  port: number;
  service: string;
  banner?: string;
  country: string;
  city: string;
  asn: string;
  riskLevel: 'Critical' | 'High' | 'Medium' | 'Low';
  vulnerabilities: string[];
  lastSeen: string;
}

export interface GeographicData {
  country: string;
  code: string;
  count: number;
  risk: number;
  lat: number;
  lng: number;
}

export interface PortStats {
  port: number;
  service: string;
  count: number;
  percentage?: number;
  risk?: 'critical' | 'high' | 'medium' | 'low';
}

// Skill 相关类型
export interface TrustedSkill {
  id: string;
  name: string;
  version: string;
  description: string;
  category: string;
  maintainer: string;
  downloads: number;
  rating: number;
  verified: boolean;
  lastUpdated: string;
  securityScore: number;
  permissions: string[];
  repository: string;
}

export interface SuspiciousSkill {
  id: string;
  name: string;
  version: string;
  description: string;
  category: string;
  maintainer: string;
  detectionReason: string[];
  riskLevel: 'Critical' | 'High' | 'Medium' | 'Low';
  firstDetected: string;
  reportCount: number;
  analysisStatus: 'confirmed' | 'under_review' | 'false_positive';
  maliciousBehaviors: string[];
}

export interface SkillAnalysis {
  skillId: string;
  basicInfo: {
    name: string;
    version: string;
    size: string;
    language: string;
    architecture: string;
  };
  securityAnalysis: {
    overallScore: number;
    codeQuality: number;
    permissionUsage: number;
    networkBehavior: number;
    fileSystemAccess: number;
  };
  staticAnalysis: {
    malwareSignatures: number;
    suspiciousPatterns: number;
    vulnerabilities: Array<{
      type: string;
      severity: string;
      location: string;
      description: string;
    }>;
  };
  dynamicAnalysis: {
    networkConnections: Array<{
      host: string;
      port: number;
      protocol: string;
      purpose: string;
    }>;
    fileOperations: Array<{
      path: string;
      operation: string;
      purpose: string;
    }>;
    systemCalls: string[];
  };
  dependencies: Array<{
    name: string;
    version: string;
    vulnerabilities: number;
    license: string;
  }>;
}

// API 响应类型
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: {
    message: string;
    stack?: string;
  };
  timestamp: string;
}

export interface PaginationInfo {
  page: number;
  limit: number;
  total: number;
  totalPages: number;
}

export interface PaginatedResponse<T> extends ApiResponse<{
  items: T[];
  pagination: PaginationInfo;
}> {}

// 配置类型
export interface DashboardConfig {
  refreshInterval: number;
  alertThresholds: {
    criticalRisks: number;
    exposedServices: number;
    suspiciousSkills: number;
  };
  visualization: {
    theme: 'light' | 'dark';
    chartColors: string[];
    mapStyle: string;
  };
}
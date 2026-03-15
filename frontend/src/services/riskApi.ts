import { useEffect, useState } from 'react';

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

export interface RiskItem {
  id: string;
  title: string;
  description: string;
  severity: 'Critical' | 'High' | 'Medium' | 'Low';
  score: number;
  category: string;
  affectedVersions?: string[];
  mitigation?: string;
  cveId?: string;
  lastUpdated: string;
}

export interface RiskTrendPoint {
  date: string;
  critical: number;
  high: number;
  medium: number;
  low: number;
}

export interface VulnerabilityItem {
  index: number;
  title: string;
  stage: string;
  reason: string;
  vulnerabilityId: string;
  severity: 'Critical' | 'High' | 'Moderate' | 'Low' | string;
  affectedVersions: string;
  cve: string;
  cwe: string;
  link: string;
  vulnerabilityNatureId: string;
  vulnerabilityNatureLabel: string;
  top10PrimaryId: string;
  top10PrimaryLabel: string;
  top10MatchIds: string[];
  top10MatchLabels: string[];
  top10Rank: number | null;
  top10MatchCount: number;
  mappingConfidence: number;
  analysisReason: string;
}

const getApiBase = () => {
  if (typeof window !== 'undefined') {
    return '/api';
  }
  return 'http://localhost:3005/api';
};

const API_BASE = getApiBase();

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'X-Watchboard-Client': 'web',
    },
  });
  const data = await response.json();

  if (!response.ok || !data.success) {
    throw new Error(data.error?.message || `Request failed: ${response.status}`);
  }

  return data.data as T;
}

export const riskAPI = {
  getStats() {
    return request<RiskStats>('/risks/stats/summary');
  },

  async getTop10() {
    const data = await request<{ risks: RiskItem[]; total: number; lastUpdated: string }>('/risks/top10');
    return data;
  },

  async getTrends(timeRange = '7d') {
    return request<{ timeRange: string; data: RiskTrendPoint[] }>(`/risks/trends/${timeRange}`);
  },

  async getVulnerabilities() {
    return request<{
      total: number;
      summary: {
        llmSpecific: number;
        generalSoftware: number;
        mappedTop10: number;
      };
      vulnerabilities: VulnerabilityItem[];
      lastUpdated: string;
    }>('/risks/vulnerabilities');
  },
};

export const useRiskDashboardData = () => {
  const [stats, setStats] = useState<RiskStats | null>(null);
  const [topRisks, setTopRisks] = useState<RiskItem[]>([]);
  const [trends, setTrends] = useState<RiskTrendPoint[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [statsData, top10Data, trendsData] = await Promise.all([
        riskAPI.getStats(),
        riskAPI.getTop10(),
        riskAPI.getTrends('7d'),
      ]);
      setStats(statsData);
      setTopRisks(top10Data.risks || []);
      setTrends(trendsData.data || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  return { stats, topRisks, trends, loading, error, refetch: load };
};

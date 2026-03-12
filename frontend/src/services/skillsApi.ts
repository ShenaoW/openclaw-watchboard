import { useEffect, useState } from 'react';

export interface SkillStats {
  totalSkills: number;
  sourceDistribution: Array<{
    source: string;
    count: number;
  }>;
  securityDistribution: {
    safe: number;
    suspicious: number;
    malicious: number;
    unknown: number;
  };
  topDevelopers: Array<{
    developer: string;
    skillCount: number;
    safeCount: number;
    suspiciousCount: number;
    maliciousCount: number;
  }>;
  topCategories: Array<{
    category: string;
    count: number;
    percentage: number;
  }>;
  popularSkillsBySource: Record<
    string,
    Array<{
      name: string;
      downloads?: number;
      rating?: number;
      classification: string;
    }>
  >;
}

export interface SkillDetail {
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
  source: 'clawhub' | 'skills.rest' | 'skillsmp' | 'skills.sh' | 'gendigital' | 'other' | string;
  classification: 'safe' | 'suspicious' | 'malicious' | 'unknown';
}

const getApiBase = () => {
  if (typeof window !== 'undefined') {
    return '/api';
  }
  return 'http://localhost:3005/api';
};

const API_BASE = getApiBase();

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  const data = await response.json();

  if (!response.ok || !data.success) {
    throw new Error(data.error?.message || `Request failed: ${response.status}`);
  }

  return data.data as T;
}

export const skillsAPI = {
  getStats(): Promise<SkillStats> {
    return request('/skills/stats');
  },

  getSkills(filters?: {
    classification?: string;
    source?: string;
    category?: string;
    search?: string;
    page?: number;
    limit?: number;
  }): Promise<{
    skills: SkillDetail[];
    pagination: {
      page: number;
      limit: number;
      total: number;
      totalPages: number;
    };
  }> {
    const params = new URLSearchParams();

    Object.entries(filters || {}).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        params.append(key, String(value));
      }
    });

    const endpoint =
      filters?.classification === 'malicious'
        ? '/skills/malicious'
        : filters?.classification === 'unknown'
          ? '/skills/pending'
        : filters?.classification === 'suspicious'
          ? '/skills/suspicious'
          : '/skills/trusted';

    return request(`${endpoint}?${params.toString()}`);
  },

  getSkillAnalysis(skillId: string) {
    return request(`/skills/analysis/${encodeURIComponent(skillId)}`);
  },

  reportSkill(skillData: { skillId: string; reason: string; description: string }) {
    return request('/skills/report', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(skillData),
    });
  },

  verifySkill(skillData: { skillId: string; source: string; verifyType: string }) {
    return request('/skills/verify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(skillData),
    });
  },
};

export const useSkillsData = () => {
  const [stats, setStats] = useState<SkillStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadStats = async () => {
    setLoading(true);
    setError(null);
    try {
      setStats(await skillsAPI.getStats());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStats();
  }, []);

  return { stats, loading, error, refetch: loadStats };
};

export const useSkillsList = (filters?: {
  classification?: string;
  source?: string;
  category?: string;
  search?: string;
  page?: number;
  limit?: number;
}) => {
  const [skills, setSkills] = useState<SkillDetail[]>([]);
  const [pagination, setPagination] = useState({
    page: 1,
    limit: 20,
    total: 0,
    totalPages: 0,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadSkills = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await skillsAPI.getSkills(filters);
      setSkills(result.skills);
      setPagination(result.pagination);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSkills();
  }, [JSON.stringify(filters)]);

  return { skills, pagination, loading, error, refetch: loadSkills };
};

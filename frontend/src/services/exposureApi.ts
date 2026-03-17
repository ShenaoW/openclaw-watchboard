import { useState, useEffect } from 'react';

export interface ExposureStats {
  totalExposedServices: number;
  activeInstances: number;
  chinaExposedServices: number;
  chinaActiveInstances: number;
  countryCount: number;
  provinceCount: number;
  cityCount: number;
  historicalVulnerableInstances: number;
  historicalVulnerableActiveInstances: number;
  historicalMatchedVulnerabilityCount: number;
  deltas: {
    totalExposedServices: number;
    activeInstances: number;
    chinaExposedServices: number;
    chinaActiveInstances: number;
    countryCount: number;
    provinceCount: number;
    cityCount: number;
    historicalVulnerableInstances: number;
    historicalMatchedVulnerabilityCount: number;
  };
  lastScanTime: string;
  topCountries: Array<{
    country: string;
    count: number;
  }>;
  topPorts: Array<{
    port: number;
    service: string;
    count: number;
  }>;
}

export interface ExposedService {
  id: string;
  ip: string;
  maskedIp?: string;
  hostname: string | null;
  port: number;
  service: string;
  banner: string;
  country: string;
  city: string;
  asn: string;
  organization?: string;
  isp?: string;
  runtimeStatus: string;
  serverVersion?: string | null;
  historicalVulnCount?: number;
  historicalVulnMaxSeverity?: string | null;
  historicalVulnMatches?: Array<{
    vulnerability_id: string;
    title: string;
    severity: string;
    affected_versions: string;
    cve: string;
  }>;
  isChinaInstance?: boolean;
  province?: string | null;
  cnCity?: string | null;
  lastSeen: string;
  firstSeen?: string;
  status?: string;
  authenticated?: string;
  active?: string;
  credentialsLeaked?: string;
  hasMcp?: string;
  aptGroups?: string;
  domains?: string;
}

export interface GeographicData {
  world: Array<{
    country: string;
    code: string;
    count: number;
    lat: number;
    lng: number;
  }>;
  heatmap: Array<{
    lat: number;
    lng: number;
    intensity: number;
  }>;
  china: Array<{
    province: string;
    count: number;
    lat: number;
    lng: number;
  }>;
  provinceTop: Array<{
    province: string;
    count: number;
  }>;
  cityTop: Array<{
    province: string;
    count: number;
  }>;
}

export interface PortDistribution {
  common: Array<{
    port: number;
    service: string;
    count: number;
    percentage: number;
  }>;
}

export interface ExposureTrendPoint {
  date: string;
  firstSeen: number;
  lastSeen: number;
  active: number;
}

// 动态获取API基础URL，支持不同环境
const getApiBase = () => {
  if (typeof window !== 'undefined') {
    return '/api';
  }
  return 'http://localhost:3005/api';
};

const API_BASE = getApiBase();

const API_HEADERS = {
  'X-Watchboard-Client': 'web',
};

export const exposureAPI = {
  // 获取暴露统计概览
  async getOverview(): Promise<ExposureStats> {
    const response = await fetch(`${API_BASE}/exposure/overview`, {
      headers: API_HEADERS,
    });
    const data = await response.json();
    if (!response.ok || !data.success) {
      throw new Error(data.error?.message || 'Failed to fetch exposure overview');
    }
    return data.data;
  },

  // 获取暴露服务列表
  async getServices(filters?: {
    status?: string;
    runtimeStatus?: string;
    chinaScope?: string;
    versionStatus?: string;
    historicalVulnStatus?: string;
    historicalVulnCountRange?: string;
    country?: string;
    isp?: string;
    credentials_leaked?: string;
    search?: string;
    page?: number;
    limit?: number;
  }): Promise<{
    services: ExposedService[];
    pagination: {
      page: number;
      limit: number;
      total: number;
      totalPages: number;
    };
  }> {
    const params = new URLSearchParams();

    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          params.append(key, String(value));
        }
      });
    }

    const response = await fetch(`${API_BASE}/exposure/services?${params}`, {
      headers: API_HEADERS,
    });
    const data = await response.json();
    if (!data.success) {
      throw new Error(data.error?.message || 'Failed to fetch exposed services');
    }

    return {
      services: data.data.services,
      pagination: data.data.pagination
    };
  },

  // 获取地理分布数据
  async getGeographicDistribution(): Promise<GeographicData> {
    const response = await fetch(`${API_BASE}/exposure/geography`, {
      headers: API_HEADERS,
    });
    const data = await response.json();
    if (!response.ok || !data.success) {
      throw new Error(data.error?.message || 'Failed to fetch geographic distribution');
    }
    return data.data;
  },

  // 获取端口分布数据
  async getPortDistribution(): Promise<PortDistribution> {
    const response = await fetch(`${API_BASE}/exposure/ports`, {
      headers: API_HEADERS,
    });
    const data = await response.json();
    if (!data.success) {
      throw new Error(data.error?.message || 'Failed to fetch port distribution');
    }
    return data.data;
  },

  async getTrends(timeRange = '30d'): Promise<{
    timeRange: string;
    data: ExposureTrendPoint[];
  }> {
    const response = await fetch(`${API_BASE}/exposure/trends?timeRange=${encodeURIComponent(timeRange)}`, {
      headers: API_HEADERS,
    });
    const data = await response.json();
    if (!data.success) {
      throw new Error(data.error?.message || 'Failed to fetch exposure trends');
    }
    return data.data;
  },

  // 搜索特定目标
  async searchTarget(target: string): Promise<{
    target: string;
    found: boolean;
    services: ExposedService[];
  }> {
    const response = await fetch(`${API_BASE}/exposure/search/${encodeURIComponent(target)}`, {
      headers: API_HEADERS,
    });
    const data = await response.json();
    if (!data.success) {
      throw new Error(data.error?.message || 'Failed to search target');
    }
    return data.data;
  },

  // 触发扫描
  async triggerScan(scanData: {
    targets: string[];
    scanType?: string;
  }): Promise<{
    id: string;
    targets: string[];
    scanType: string;
    status: string;
    createdAt: string;
  }> {
    const response = await fetch(`${API_BASE}/exposure/scan`, {
      method: 'POST',
      headers: {
        ...API_HEADERS,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(scanData),
    });
    const data = await response.json();
    if (!data.success) {
      throw new Error(data.error?.message || 'Failed to trigger scan');
    }
    return data.data;
  }
};

// Custom hook for exposure overview data
export const useExposureOverview = () => {
  const [overview, setOverview] = useState<ExposureStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadOverview = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await exposureAPI.getOverview();
      setOverview(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOverview();
  }, []);

  return { overview, loading, error, refetch: loadOverview };
};

// Custom hook for exposed services list
export const useExposedServices = (filters?: {
  status?: string;
  runtimeStatus?: string;
  chinaScope?: string;
  versionStatus?: string;
  historicalVulnStatus?: string;
  historicalVulnCountRange?: string;
  country?: string;
  isp?: string;
  credentials_leaked?: string;
  search?: string;
  page?: number;
  limit?: number;
}) => {
  const [services, setServices] = useState<ExposedService[]>([]);
  const [pagination, setPagination] = useState({
    page: 1,
    limit: 20,
    total: 0,
    totalPages: 0
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadServices = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await exposureAPI.getServices(filters);
      setServices(data.services);
      setPagination(data.pagination);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadServices();
  }, [JSON.stringify(filters)]);

  return { services, pagination, loading, error, refetch: loadServices };
};

// Custom hook for geographic distribution
export const useGeographicData = () => {
  const [geoData, setGeoData] = useState<GeographicData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadGeoData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await exposureAPI.getGeographicDistribution();
      setGeoData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadGeoData();
  }, []);

  return { geoData, loading, error, refetch: loadGeoData };
};

// Custom hook for port distribution
export const usePortDistribution = () => {
  const [portData, setPortData] = useState<PortDistribution | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadPortData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await exposureAPI.getPortDistribution();
      setPortData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPortData();
  }, []);

  return { portData, loading, error, refetch: loadPortData };
};

export const useExposureTrends = (timeRange = '30d') => {
  const [trendData, setTrendData] = useState<ExposureTrendPoint[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadTrendData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await exposureAPI.getTrends(timeRange);
      setTrendData(data.data || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTrendData();
  }, [timeRange]);

  return { trendData, loading, error, refetch: loadTrendData };
};

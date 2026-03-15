export interface AnalyticsSummary {
  totalPageViews: number;
  totalUniqueVisitors: number;
  firstRecordedAt: string | null;
  lastRecordedAt: string | null;
}

const API_HEADERS = {
  'Content-Type': 'application/json',
  'X-Watchboard-Client': 'web',
};

async function parseResponse<T>(response: Response): Promise<T> {
  const data = await response.json();
  if (!response.ok || !data.success) {
    throw new Error(data.error?.message || 'Analytics request failed');
  }

  return data.data as T;
}

export const analyticsApi = {
  async getSummary(): Promise<AnalyticsSummary> {
    const response = await fetch('/api/analytics/summary', {
      headers: {
        'X-Watchboard-Client': 'web',
      },
    });

    return parseResponse<AnalyticsSummary>(response);
  },

  async recordPageView(pagePath: string): Promise<void> {
    const response = await fetch('/api/analytics/page-view', {
      method: 'POST',
      headers: API_HEADERS,
      body: JSON.stringify({ pagePath }),
      credentials: 'same-origin',
      keepalive: true,
    });

    if (!response.ok && response.status !== 204) {
      const data = await response.json().catch(() => null);
      throw new Error(data?.error?.message || 'Failed to record page view');
    }
  },
};

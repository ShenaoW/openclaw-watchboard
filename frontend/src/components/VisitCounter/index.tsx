import { EyeOutlined } from '@ant-design/icons';
import type { SiderMenuProps } from '@ant-design/pro-components';
import { Spin } from 'antd';
import React, { useEffect, useState } from 'react';
import { analyticsApi, type AnalyticsSummary } from '@/services/analyticsApi';

const EVENT_NAME = 'watchboard:analytics-updated';

const footerStyle: React.CSSProperties = {
  padding: '8px 12px 14px',
  margin: '0 12px',
  color: 'rgba(0, 0, 0, 0.45)',
  fontSize: 12,
  lineHeight: 1.4,
};

function formatCount(value: number) {
  return new Intl.NumberFormat('zh-CN').format(value);
}

export function VisitCounter({ collapsed }: Pick<SiderMenuProps, 'collapsed'>) {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;

    const loadSummary = async () => {
      try {
        const nextSummary = await analyticsApi.getSummary();
        if (mounted) {
          setSummary(nextSummary);
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    const handleRefresh = () => {
      void loadSummary();
    };

    void loadSummary();
    window.addEventListener(EVENT_NAME, handleRefresh);

    return () => {
      mounted = false;
      window.removeEventListener(EVENT_NAME, handleRefresh);
    };
  }, []);

  if (collapsed) {
    return (
      <div style={{ ...footerStyle, padding: '8px 0 12px', textAlign: 'center' }}>
        {loading ? <Spin size="small" /> : <EyeOutlined style={{ fontSize: 14, color: 'rgba(0, 0, 0, 0.45)' }} />}
      </div>
    );
  }

  return (
    <div style={footerStyle}>
      {loading ? (
        <div style={{ textAlign: 'left', padding: '2px 0' }}>
          <Spin size="small" />
        </div>
      ) : (
        <div>
          <EyeOutlined style={{ marginRight: 6 }} />
          累计访问 {formatCount(summary?.totalPageViews || 0)}
        </div>
      )}
    </div>
  );
}

export const analyticsUpdateEventName = EVENT_NAME;

import { history } from '@umijs/max';
import React, { useEffect, useRef } from 'react';
import { analyticsUpdateEventName } from '@/components/VisitCounter';
import { analyticsApi } from '@/services/analyticsApi';

function buildTrackKey(pathname: string, search: string) {
  return `${pathname}${search}`;
}

export function GlobalAnalyticsTracker() {
  const lastTrackedKeyRef = useRef<string>('');

  useEffect(() => {
    const sendPageView = async (pathname: string, search: string) => {
      const nextKey = buildTrackKey(pathname, search);
      if (!nextKey || nextKey === lastTrackedKeyRef.current || pathname.startsWith('/user/')) {
        return;
      }

      lastTrackedKeyRef.current = nextKey;

      try {
        await analyticsApi.recordPageView(nextKey);
        window.dispatchEvent(new Event(analyticsUpdateEventName));
      } catch (error) {
        console.error('Failed to record page view', error);
      }
    };

    void sendPageView(history.location.pathname, history.location.search);

    const unlisten = history.listen(({ location }) => {
      void sendPageView(location.pathname, location.search);
    });

    return () => {
      unlisten();
    };
  }, []);

  return null;
}

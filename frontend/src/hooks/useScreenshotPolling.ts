import { useCallback, useEffect, useRef, useState } from 'react';
import { getScreenshot, type ScreenshotResponse } from '../api';
import { usePageVisibility } from './usePageVisibility';

interface UseScreenshotPollingOptions {
  deviceId: string;
  enabled: boolean;
  pollDelayMs: number;
}

interface UseScreenshotPollingResult {
  screenshot: ScreenshotResponse | null;
  /** Immediately fetch a fresh screenshot (e.g., after a control action). */
  triggerRefresh: () => Promise<void>;
}

export function useScreenshotPolling({
  deviceId,
  enabled,
  pollDelayMs,
}: UseScreenshotPollingOptions): UseScreenshotPollingResult {
  const isPageVisible = usePageVisibility();
  const [screenshot, setScreenshot] = useState<ScreenshotResponse | null>(null);
  const isFetchingRef = useRef(false);
  // Store latest screenshot in a ref to avoid stale closure in the polling loop
  const screenshotRef = useRef<ScreenshotResponse | null>(null);

  const fetchScreenshot = useCallback(async () => {
    if (isFetchingRef.current) return;

    isFetchingRef.current = true;
    try {
      const data = await getScreenshot(deviceId);
      if (data.success) {
        // Clear previous screenshot before storing new one to allow GC
        screenshotRef.current = null;
        setScreenshot(null);
        screenshotRef.current = data;
        setScreenshot(data);
      }
    } catch (error) {
      console.error('Failed to fetch screenshot:', error);
    } finally {
      isFetchingRef.current = false;
    }
  }, [deviceId]);

  // Expose triggerRefresh so callers (e.g. ScrcpyPlayer) can force an immediate fetch.
  // If a fetch is already in-flight, wait for it to complete rather than starting a duplicate.
  const triggerRefresh = useCallback(async () => {
    if (isFetchingRef.current) {
      // A fetch is already in progress — wait for it to finish
      await new Promise<void>(resolve => {
        const interval = setInterval(() => {
          if (!isFetchingRef.current) {
            clearInterval(interval);
            resolve();
          }
        }, 50);
      });
    } else {
      await fetchScreenshot();
    }
  }, [fetchScreenshot]);

  useEffect(() => {
    if (!deviceId || !enabled || !isPageVisible) {
      // Clear screenshot when disabled to free memory
      setScreenshot(null);
      screenshotRef.current = null;
      return;
    }

    let isCancelled = false;
    let timeoutId: number | null = null;

    const pollScreenshots = async () => {
      await fetchScreenshot();
      if (isCancelled) return;
      timeoutId = window.setTimeout(() => { void pollScreenshots(); }, pollDelayMs);
    };

    void pollScreenshots();

    return () => {
      isCancelled = true;
      if (timeoutId !== null) window.clearTimeout(timeoutId);
      // Release screenshot memory on cleanup
      setScreenshot(null);
      screenshotRef.current = null;
    };
  }, [deviceId, enabled, isPageVisible, pollDelayMs, fetchScreenshot]);

  return { screenshot, triggerRefresh };
}

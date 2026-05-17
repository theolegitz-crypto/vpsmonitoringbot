import { useEffect } from "react";


export function useAutoRefresh(refreshFn, intervalMs, deps = []) {
  useEffect(() => {
    let timeoutId = null;
    let stopped = false;

    async function tick() {
      if (stopped) {
        return;
      }

      if (document.visibilityState === "visible") {
        await refreshFn();
      }

      timeoutId = window.setTimeout(tick, intervalMs);
    }

    timeoutId = window.setTimeout(tick, intervalMs);

    return () => {
      stopped = true;
      if (timeoutId) {
        window.clearTimeout(timeoutId);
      }
    };
  }, deps);
}


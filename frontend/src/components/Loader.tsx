"use client";

import { useEffect, useMemo, useRef, useState } from "react";

// Contract:
// - Shows an overlay with a centered "G" and 3 rings that fill to 100%.
// - Progress advances automatically and completes on window 'load'.
// - On complete, overlay morphs into 3 horizontal ribbons then retracts.

type LoaderProps = {
  // Optional: externally provided progress (0-100). If omitted, internal timer is used.
  progress?: number;
  // Optional: allow forcing visible state for testing.
  forceVisible?: boolean;
};

export default function Loader({ progress: externalProgress, forceVisible }: LoaderProps) {
  const [progress, setProgress] = useState(0);
  const [ringProgresses, setRingProgresses] = useState([0, 0, 0]);
  const [loaded, setLoaded] = useState(false);
  const [exiting, setExiting] = useState(false);
  const [showRibbons, setShowRibbons] = useState(false);
  const [mounted, setMounted] = useState(false);
  const rafRef = useRef<number | null>(null);
  const startedRef = useRef(false);

  // Handle hydration
  useEffect(() => {
    setMounted(true);
  }, []);

  // Smooth internal progress simulation until window load.
  useEffect(() => {
    if (!mounted) return;
    
    if (externalProgress !== undefined) {
      setProgress(Math.max(0, Math.min(100, externalProgress)));
      return;
    }
    
    // Reset the started ref when mounted changes
    startedRef.current = false;
    
    if (startedRef.current) return;
    startedRef.current = true;
    
    let p = 0;
    let ringP = [0, 0, 0];
    let lastTs = 0;
    const ringSpeeds = [0.035, 0.025, 0.015]; // Different speeds: fast, medium, slow
    
    const tick = (ts: number) => {
      if (!lastTs) lastTs = ts;
      const dt = Math.min(1000, ts - lastTs); // cap delta
      lastTs = ts;
      
      // Main progress for display
      const target = loaded ? 100 : 90;
      const delta = (target - p) * 0.03 * (dt / 16.7);
      p = Math.min(target, p + delta);
      setProgress(p);
      
      // Individual ring progress with different speeds
      const newRingProgresses = ringP.map((ringProgress, idx) => {
        const ringTarget = loaded ? 100 : 90;
        const ringSpeed = ringSpeeds[idx];
        const ringDelta = (ringTarget - ringProgress) * ringSpeed * (dt / 16.7);
        return Math.min(ringTarget, ringProgress + ringDelta);
      });
      
      ringP = newRingProgresses;
      setRingProgresses([...newRingProgresses]);
      
      // Debug logging
      if (Math.floor(p) !== Math.floor(p - delta)) {
        console.log(`Progress: ${Math.floor(p)}%, Rings: [${ringP.map(r => Math.floor(r)).join(', ')}]%, Loaded: ${loaded}`);
      }
      
      if (p < 99.9 || ringP.some(r => r < 99.9)) {
        rafRef.current = requestAnimationFrame(tick);
      }
    };
    
    // Start immediately after mounting
    rafRef.current = requestAnimationFrame(tick);
    
    return () => {
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
    };
  }, [externalProgress, loaded, mounted]);

  // When window finishes loading, drive to 100 and then exit.
  useEffect(() => {
    if (!mounted) return;
    
    const onLoad = () => {
      console.log("Window loaded, setting loaded to true");
      setLoaded(true);
    };
    
    // For development, set a shorter timeout to see the complete animation
    const fallbackTimeout = setTimeout(() => {
      console.log("Fallback timeout triggered");
      setLoaded(true);
    }, 3000);
    
    if (document.readyState === "complete") {
      console.log("Document already complete");
      onLoad();
    } else {
      console.log("Adding load listener");
      window.addEventListener("load", onLoad, { once: true });
    }
    
    return () => {
      window.removeEventListener("load", onLoad);
      clearTimeout(fallbackTimeout);
    };
  }, [mounted]);

  useEffect(() => {
    if (!loaded) return;
    // When all rings reach near 100%, start exit sequence
    const allRingsComplete = ringProgresses.every(p => p >= 99);
    if (allRingsComplete && !exiting) {
      const t = setTimeout(() => {
        console.log("Starting exit sequence - showing ribbons");
        setShowRibbons(true);
        setExiting(true);
      }, 150);
      return () => clearTimeout(t);
    }
  }, [loaded, ringProgresses, exiting]);

  const rings = useMemo(() => {
    // Define 3 rings with increasing radius
    const base = 36; // SVG viewBox units
    return [base, base + 10, base + 20].map((r, i) => ({
      r,
      key: `ring-${i}`,
    }));
  }, []);

  // Convert progress to stroke-dashoffset. Full circle length = 2πr.
  const getStrokeParams = (r: number, progressValue: number) => {
    const circumference = 2 * Math.PI * r;
    const pct = Math.max(0, Math.min(100, progressValue));
    const dashoffset = circumference * (1 - pct / 100);
    return { circumference, dashoffset };
  };

  const [hidden, setHidden] = useState(false);
  
  // Hide completely after exit animation
  useEffect(() => {
    if (exiting) {
      const hideTimeout = setTimeout(() => {
        setHidden(true);
      }, 1200); // Wait for ribbon animation to complete
      return () => clearTimeout(hideTimeout);
    }
  }, [exiting]);

  const showLoader = mounted && !hidden && (forceVisible ?? (!exiting || ringProgresses.some(p => p < 99)));

  // Don't render anything until mounted (prevents hydration mismatch)
  if (!mounted) return null;

  return (
    <>
      {/* Persistent ribbons that stay after loading */}
      {showRibbons && (
        <div className="ribbons-container">
          <div className={`ribbon fixed h-12 w-0 opacity-0 ribbon-0`} 
               style={{ top: '20%', left: '0' }} />
          <div className={`ribbon fixed h-12 w-0 opacity-0 ribbon-1`} 
               style={{ top: '50%', left: '0' }} />
          <div className={`ribbon fixed h-12 w-0 opacity-0 ribbon-2`} 
               style={{ top: '80%', left: '0' }} />
        </div>
      )}
      
      {/* Main loader overlay */}
      <div
        className={
          "loader-overlay fixed inset-0 z-50 grid place-items-center bg-[var(--background)] text-[var(--foreground)] " +
          (showLoader ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none") +
          (exiting ? " loader-exit" : "")
        }
        aria-hidden={!showLoader}
      >
      <div className="relative w-[360px] h-[360px] max-w-[80vw] max-h-[80vw]">
        <svg
          className="absolute inset-0 w-full h-full"
          viewBox="0 0 200 200"
          role="img"
          aria-label="Loading"
        >
          {/* Background faint rings */}
          {rings.map(({ r, key }, idx) => (
            <circle
              key={`bg-${key}`}
              cx="100"
              cy="100"
              r={r}
              fill="none"
              stroke="currentColor"
              strokeOpacity={0.1 + idx * 0.07}
              strokeWidth={6}
            />
          ))}
          {/* Foreground progress rings */}
          {rings.map(({ r, key }, idx) => {
            const { circumference, dashoffset } = getStrokeParams(r, ringProgresses[idx]);
            return (
              <circle
                key={key}
                cx="100"
                cy="100"
                r={r}
                fill="none"
                stroke="currentColor"
                strokeWidth={6}
                strokeLinecap="round"
                strokeDasharray={circumference}
                strokeDashoffset={dashoffset}
                className={`ring-progress ring-${idx}`}
              />
            );
          })}
        </svg>

        {/* Center G */}
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="font-bold text-7xl tracking-tight select-none">G</span>
        </div>


        </div>

        {/* Percentage for accessibility/visual debugging */}
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 text-sm opacity-70">
          {Math.round(progress)}%
        </div>
      </div>
    </>
  );
}

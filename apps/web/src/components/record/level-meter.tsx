"use client";

import { useEffect, useRef } from "react";

interface LevelMeterProps {
  analyser: AnalyserNode | null;
  className?: string;
}

/**
 * Canvas-based audio level meter for the in-browser recorder.
 * Reads from a Web Audio AnalyserNode so it stays in sync with whatever
 * the MediaRecorder is capturing without piggybacking on the recorded
 * MediaStream itself.
 */
export function LevelMeter({ analyser, className }: LevelMeterProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!analyser || !canvasRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const buffer = new Uint8Array(analyser.fftSize);
    let raf = 0;

    const draw = () => {
      analyser.getByteTimeDomainData(buffer);
      // Compute RMS for the bar level.
      let sum = 0;
      for (let i = 0; i < buffer.length; i++) {
        const v = (buffer[i] - 128) / 128;
        sum += v * v;
      }
      const rms = Math.sqrt(sum / buffer.length);
      const level = Math.min(1, rms * 2.5);

      const w = canvas.width;
      const h = canvas.height;
      ctx.clearRect(0, 0, w, h);
      // Background track.
      ctx.fillStyle = "rgba(127,127,127,0.15)";
      ctx.fillRect(0, h * 0.3, w, h * 0.4);
      // Active level.
      ctx.fillStyle = level > 0.85 ? "#e42c39" : "#34d399";
      ctx.fillRect(0, h * 0.3, w * level, h * 0.4);
      raf = requestAnimationFrame(draw);
    };
    draw();
    return () => cancelAnimationFrame(raf);
  }, [analyser]);

  return (
    <canvas
      ref={canvasRef}
      width={400}
      height={32}
      className={className ?? "h-8 w-full"}
      role="img"
      aria-label="Audio level meter"
    />
  );
}

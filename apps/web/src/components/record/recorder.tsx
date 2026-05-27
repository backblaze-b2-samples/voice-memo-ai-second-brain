"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Mic, Square, Upload as UploadIcon } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LevelMeter } from "./level-meter";
import { ApiError, uploadMemo } from "@/lib/api-client";
import { useRefresh } from "@/lib/refresh-context";

type RecorderState = "idle" | "recording" | "stopped" | "uploading";

/**
 * In-browser MediaRecorder UI. Captures a single take from the user's
 * default mic, shows a live level meter, and POSTs the resulting blob to
 * `/memos` (the recorder-specific endpoint that mirrors `/upload`).
 *
 * Browser support: every current Chrome/Edge/Firefox/Safari ships
 * MediaRecorder. Codec selection prefers `audio/webm;codecs=opus`, falling
 * back to `audio/mp4` on Safari which doesn't yet implement webm/opus.
 */
export function Recorder() {
  const router = useRouter();
  const { triggerRefresh } = useRefresh();
  const [state, setState] = useState<RecorderState>("idle");
  const [elapsedMs, setElapsedMs] = useState(0);
  const [analyser, setAnalyser] = useState<AnalyserNode | null>(null);
  const [blob, setBlob] = useState<Blob | null>(null);

  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const startedAtRef = useRef<number>(0);
  const tickRef = useRef<number | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);

  // Tidy up any in-flight stream/AudioContext on unmount.
  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach((t) => t.stop());
      audioCtxRef.current?.close().catch(() => {});
      if (tickRef.current) cancelAnimationFrame(tickRef.current);
    };
  }, []);

  const startTicker = () => {
    const tick = () => {
      setElapsedMs(Date.now() - startedAtRef.current);
      tickRef.current = requestAnimationFrame(tick);
    };
    tickRef.current = requestAnimationFrame(tick);
  };

  const stopTicker = () => {
    if (tickRef.current) cancelAnimationFrame(tickRef.current);
    tickRef.current = null;
  };

  const pickMimeType = (): string => {
    const candidates = [
      "audio/webm;codecs=opus",
      "audio/webm",
      "audio/mp4",
      "audio/ogg;codecs=opus",
    ];
    for (const c of candidates) {
      if (typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported(c)) {
        return c;
      }
    }
    return "audio/webm";
  };

  const start = async () => {
    setBlob(null);
    setElapsedMs(0);
    chunksRef.current = [];

    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : "Microphone permission denied";
      toast.error(`Couldn’t access microphone: ${msg}`);
      return;
    }
    streamRef.current = stream;

    // Live level meter — separate from the MediaRecorder's stream.
    const AudioCtxCtor =
      window.AudioContext ||
      (window as unknown as { webkitAudioContext: typeof AudioContext })
        .webkitAudioContext;
    const audioCtx = new AudioCtxCtor();
    audioCtxRef.current = audioCtx;
    const source = audioCtx.createMediaStreamSource(stream);
    const an = audioCtx.createAnalyser();
    an.fftSize = 2048;
    source.connect(an);
    setAnalyser(an);

    const mimeType = pickMimeType();
    const recorder = new MediaRecorder(stream, { mimeType });
    recorderRef.current = recorder;
    recorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) chunksRef.current.push(e.data);
    };
    recorder.onstop = () => {
      const finalBlob = new Blob(chunksRef.current, { type: mimeType });
      setBlob(finalBlob);
      setState("stopped");
      stopTicker();
      stream.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
      audioCtx.close().catch(() => {});
      audioCtxRef.current = null;
      setAnalyser(null);
    };
    recorder.start(250);
    startedAtRef.current = Date.now();
    startTicker();
    setState("recording");
  };

  const stop = () => {
    recorderRef.current?.stop();
  };

  const reset = () => {
    setBlob(null);
    setElapsedMs(0);
    setState("idle");
  };

  const upload = async () => {
    if (!blob) return;
    setState("uploading");
    const ext = blob.type.includes("mp4")
      ? "m4a"
      : blob.type.includes("ogg")
        ? "ogg"
        : "webm";
    const file = new File(
      [blob],
      `memo-${new Date().toISOString().replace(/[:.]/g, "-")}.${ext}`,
      { type: blob.type },
    );
    try {
      const result = await uploadMemo(file);
      toast.success("Memo uploaded — transcription queued");
      triggerRefresh();
      router.push(`/memos/${result.key}`);
    } catch (err) {
      const detail =
        err instanceof ApiError ? err.message : "Upload failed";
      toast.error(detail);
      setState("stopped");
    }
  };

  const seconds = Math.floor(elapsedMs / 1000);
  const mm = String(Math.floor(seconds / 60)).padStart(2, "0");
  const ss = String(seconds % 60).padStart(2, "0");

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">Record a memo</CardTitle>
      </CardHeader>
      <CardContent className="p-6 space-y-4">
        <div className="text-3xl font-mono tabular-nums tracking-tight">
          {mm}:{ss}
        </div>
        <LevelMeter analyser={analyser} />
        <div className="flex flex-wrap items-center gap-2">
          {state === "idle" && (
            <Button onClick={start}>
              <Mic className="h-4 w-4" />
              Start recording
            </Button>
          )}
          {state === "recording" && (
            <Button variant="destructive" onClick={stop}>
              <Square className="h-4 w-4" />
              Stop
            </Button>
          )}
          {state === "stopped" && blob && (
            <>
              <audio
                controls
                src={URL.createObjectURL(blob)}
                className="w-full"
              />
              <div className="flex w-full items-center gap-2">
                <Button onClick={upload}>
                  <UploadIcon className="h-4 w-4" />
                  Save to B2
                </Button>
                <Button variant="ghost" onClick={reset}>
                  Discard
                </Button>
              </div>
            </>
          )}
          {state === "uploading" && (
            <Button disabled>Uploading…</Button>
          )}
        </div>
        <p className="text-xs text-muted-foreground">
          Recording captures one take from your default microphone using the
          browser’s MediaRecorder API. Files are uploaded to{" "}
          <code className="font-mono">audio/</code> in your B2 bucket and the
          transcription pipeline fires automatically.
        </p>
      </CardContent>
    </Card>
  );
}

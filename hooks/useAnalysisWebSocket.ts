/**
 * useAnalysisWebSocket
 *
 * React hook that drives the real-time code analysis progress flow over a
 * WebSocket connection (Prompt 14).
 *
 * Protocol
 * --------
 * The hook connects to `WS /api/ws/analyze` (auto-derived from
 * `NEXT_PUBLIC_API_URL` by swapping the http(s) scheme for ws(s)).
 *
 * Once `analyze(code, language)` is called the hook:
 *  1. Opens a fresh WebSocket connection.
 *  2. Sends `{"code": "…", "language": "…"}`.
 *  3. Receives progress frames and updates `stage`:
 *       "scanning"  → "analyzing" → "completed"  (happy path)
 *       "error"                                   (any failure)
 *  4. On `"completed"` the `result` field is populated.
 *  5. Closes and cleans up the socket.
 *
 * Usage
 * -----
 * ```tsx
 * const { stage, result, errorMessage, analyze, reset } = useAnalysisWebSocket();
 *
 * // Start analysis
 * analyze('print("hello")', 'python');
 *
 * // React to progress
 * if (stage === 'scanning')   { ... }
 * if (stage === 'completed')  { console.log(result); }
 * ```
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import type { AnalyzeResponse } from '@/services/api';
import { API_BASE_URL } from '@/utils/constants';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Progress stage reported by the WebSocket server. */
export type AnalysisStage = 'idle' | 'scanning' | 'analyzing' | 'completed' | 'error';

export interface UseAnalysisWebSocketResult {
  /** Current progress stage. */
  stage: AnalysisStage;
  /** Human-readable status message from the last server frame. */
  statusMessage: string;
  /** Full analysis result – populated only when `stage === "completed"`. */
  result: AnalyzeResponse | null;
  /** Error description – populated only when `stage === "error"`. */
  errorMessage: string;
  /**
   * Start a new WebSocket analysis session.
   * No-op if a session is already in progress.
   */
  analyze: (code: string, language: 'python' | 'javascript', token?: string) => void;
  /** Reset all state back to idle (cancels any running session). */
  reset: () => void;
}

// ---------------------------------------------------------------------------
// WS URL derivation
// ---------------------------------------------------------------------------

function buildWsUrl(): string {
  // Convert http(s)://host/api → ws(s)://host/api
  return API_BASE_URL.replace(/^http/, 'ws');
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useAnalysisWebSocket(): UseAnalysisWebSocketResult {
  const [stage, setStage] = useState<AnalysisStage>('idle');
  const [statusMessage, setStatusMessage] = useState('');
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState('');

  // Keep a ref to the current WebSocket so we can cancel it on unmount / reset
  const wsRef = useRef<WebSocket | null>(null);

  // Tear down the socket on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, []);

  const reset = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.close();
      wsRef.current = null;
    }
    setStage('idle');
    setStatusMessage('');
    setResult(null);
    setErrorMessage('');
  }, []);

  const analyze = useCallback(
    (code: string, language: 'python' | 'javascript', token?: string) => {
      // Don't open a second connection if one is running
      if (stage !== 'idle' && stage !== 'completed' && stage !== 'error') return;

      // Clean up any lingering socket
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
        wsRef.current = null;
      }

      setStage('scanning');
      setStatusMessage('Connecting…');
      setResult(null);
      setErrorMessage('');

      const baseUrl = buildWsUrl();
      const url = token ? `${baseUrl}/ws/analyze?token=${encodeURIComponent(token)}` : `${baseUrl}/ws/analyze`;

      let ws: WebSocket;
      try {
        ws = new WebSocket(url);
      } catch {
        setStage('error');
        setErrorMessage('Failed to open WebSocket connection.');
        return;
      }

      wsRef.current = ws;

      ws.onopen = () => {
        ws.send(JSON.stringify({ code, language }));
      };

      ws.onmessage = (event: MessageEvent) => {
        let frame: {
          stage: string;
          message?: string;
          result?: AnalyzeResponse;
        };

        try {
          frame = JSON.parse(event.data as string);
        } catch {
          return; // ignore malformed frames
        }

        const serverStage = frame.stage;

        if (serverStage === 'scanning') {
          setStage('scanning');
          setStatusMessage(frame.message ?? 'Scanning…');
        } else if (serverStage === 'analyzing') {
          setStage('analyzing');
          setStatusMessage(frame.message ?? 'Analyzing…');
        } else if (serverStage === 'completed') {
          setStage('completed');
          setStatusMessage(frame.message ?? 'Complete!');
          if (frame.result) {
            setResult(frame.result as AnalyzeResponse);
          }
        } else if (serverStage === 'error') {
          setStage('error');
          setErrorMessage(frame.message ?? 'An error occurred.');
          setStatusMessage('');
        }
      };

      ws.onerror = () => {
        setStage('error');
        setErrorMessage('WebSocket connection error. Is the backend running?');
      };

      ws.onclose = (event: CloseEvent) => {
        wsRef.current = null;
        // Only treat as error if the server closed unexpectedly and we aren't
        // already in a terminal state
        if (event.code !== 1000 && event.code !== 1001) {
          setStage((prev) => {
            if (prev !== 'completed' && prev !== 'error') {
              setErrorMessage('Connection closed unexpectedly.');
              return 'error';
            }
            return prev;
          });
        }
      };
    },
    [stage]
  );

  return { stage, statusMessage, result, errorMessage, analyze, reset };
}

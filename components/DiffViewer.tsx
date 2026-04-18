/**
 * DiffViewer – side-by-side code diff component.
 *
 * Computes a line-level diff between `original` and `fixed` using a
 * pure-TypeScript LCS (longest common subsequence) algorithm — no external
 * diff library required.
 *
 * Each line is tagged as:
 *   "unchanged" – present in both versions (shown on both sides)
 *   "removed"   – only in original (red background, left panel only)
 *   "added"     – only in fixed   (green background, right panel only)
 */

import React, { useMemo } from 'react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type LineKind = 'unchanged' | 'removed' | 'added';

interface DiffLine {
  kind: LineKind;
  lineOrig: number | null;   // 1-based line number in original, or null
  lineFix: number | null;    // 1-based line number in fixed, or null
  content: string;
}

// ---------------------------------------------------------------------------
// Pure LCS diff algorithm
// ---------------------------------------------------------------------------

/**
 * Compute a line-level diff between two arrays of strings.
 * Returns an array of DiffLine entries in display order.
 */
function computeDiff(origLines: string[], fixedLines: string[]): DiffLine[] {
  const m = origLines.length;
  const n = fixedLines.length;

  // Build LCS table
  const dp: number[][] = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0));
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (origLines[i - 1] === fixedLines[j - 1]) {
        dp[i][j] = dp[i - 1][j - 1] + 1;
      } else {
        dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
      }
    }
  }

  // Backtrack to produce diff
  const result: DiffLine[] = [];
  let i = m;
  let j = n;

  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && origLines[i - 1] === fixedLines[j - 1]) {
      result.push({ kind: 'unchanged', lineOrig: i, lineFix: j, content: origLines[i - 1] });
      i--;
      j--;
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      result.push({ kind: 'added', lineOrig: null, lineFix: j, content: fixedLines[j - 1] });
      j--;
    } else {
      result.push({ kind: 'removed', lineOrig: i, lineFix: null, content: origLines[i - 1] });
      i--;
    }
  }

  return result.reverse();
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

interface PanelProps {
  title: string;
  lines: DiffLine[];
  side: 'left' | 'right';
}

const Panel: React.FC<PanelProps> = ({ title, lines, side }) => {
  const isLeft = side === 'left';

  return (
    <div className="flex-1 min-w-0 flex flex-col overflow-hidden border border-gray-200 rounded-lg">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-2 bg-gray-50 border-b border-gray-200">
        <span
          className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${
            isLeft
              ? 'bg-red-100 text-red-700'
              : 'bg-green-100 text-green-700'
          }`}
        >
          {isLeft ? 'Original' : 'Fixed'}
        </span>
        <span className="text-xs text-gray-500 truncate">{title}</span>
      </div>

      {/* Code area */}
      <div className="overflow-auto flex-1">
        <table className="w-full text-xs font-mono border-collapse">
          <tbody>
            {lines.map((dl, idx) => {
              // Skip lines that don't belong on this side
              if (isLeft && dl.kind === 'added') return null;
              if (!isLeft && dl.kind === 'removed') return null;

              const lineNum = isLeft ? dl.lineOrig : dl.lineFix;

              let rowBg = '';
              if (dl.kind === 'removed' && isLeft) rowBg = 'bg-red-50';
              if (dl.kind === 'added' && !isLeft) rowBg = 'bg-green-50';

              let numBg = '';
              if (dl.kind === 'removed' && isLeft) numBg = 'bg-red-100 text-red-500';
              else if (dl.kind === 'added' && !isLeft) numBg = 'bg-green-100 text-green-600';
              else numBg = 'bg-gray-50 text-gray-400';

              let prefix = ' ';
              if (dl.kind === 'removed' && isLeft) prefix = '−';
              if (dl.kind === 'added' && !isLeft) prefix = '+';

              return (
                <tr key={idx} className={rowBg}>
                  {/* Line number */}
                  <td
                    className={`select-none text-right px-2 py-0 w-10 border-r border-gray-200 ${numBg}`}
                    style={{ userSelect: 'none' }}
                  >
                    {lineNum ?? ''}
                  </td>
                  {/* Change marker */}
                  <td
                    className={`select-none text-center px-1 w-5 border-r border-gray-200 ${numBg}`}
                    style={{ userSelect: 'none' }}
                  >
                    {prefix}
                  </td>
                  {/* Content */}
                  <td className="px-3 py-0.5 whitespace-pre text-gray-800">
                    {dl.content}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// DiffViewer
// ---------------------------------------------------------------------------

export interface DiffViewerProps {
  original: string;
  fixed: string;
  summary?: string;
  filename?: string;
}

const DiffViewer: React.FC<DiffViewerProps> = ({
  original,
  fixed,
  summary,
  filename = 'code',
}) => {
  const diff = useMemo(() => {
    const origLines = original.split('\n');
    const fixedLines = fixed.split('\n');
    return computeDiff(origLines, fixedLines);
  }, [original, fixed]);

  const removedCount = diff.filter((d) => d.kind === 'removed').length;
  const addedCount = diff.filter((d) => d.kind === 'added').length;
  const isUnchanged = removedCount === 0 && addedCount === 0;

  return (
    <div className="space-y-3">
      {/* Stats bar */}
      <div className="flex items-center gap-4 text-xs text-gray-500">
        {isUnchanged ? (
          <span className="text-green-700 font-medium">✅ No changes — code was already clean</span>
        ) : (
          <>
            <span className="text-red-600 font-medium">−{removedCount} removed</span>
            <span className="text-green-600 font-medium">+{addedCount} added</span>
          </>
        )}
      </div>

      {/* Summary */}
      {summary && (
        <div className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-3">
          <p className="text-xs font-semibold text-blue-800 mb-1">Changes summary</p>
          <pre className="text-xs text-blue-700 whitespace-pre-wrap font-sans">{summary}</pre>
        </div>
      )}

      {/* Side-by-side panels */}
      <div className="flex gap-3 overflow-auto" style={{ maxHeight: '70vh' }}>
        <Panel title={filename} lines={diff} side="left" />
        <Panel title={filename} lines={diff} side="right" />
      </div>
    </div>
  );
};

export default DiffViewer;

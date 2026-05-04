/**
 * Tiny line-based unified diff. Used by the version diff viewer modal
 * to compare two ``config_json`` snapshots; we don't need a full
 * Myers diff for our scale (config files are ≤ a few hundred lines).
 *
 * Algorithm: longest-common-subsequence on lines, then walk the LCS
 * to emit a sequential ``DiffLine`` stream. Output keeps original line
 * numbers for both sides so the renderer can show gutters.
 */

export type DiffOp = "context" | "add" | "remove";

export interface DiffLine {
  op: DiffOp;
  /** Old-side line number (1-based) when op != "add". */
  oldLine: number | null;
  /** New-side line number (1-based) when op != "remove". */
  newLine: number | null;
  text: string;
}

export function diffLines(oldText: string, newText: string): DiffLine[] {
  const a = oldText.split("\n");
  const b = newText.split("\n");
  const m = a.length;
  const n = b.length;

  // LCS table
  const lcs: number[][] = Array.from({ length: m + 1 }, () =>
    new Array(n + 1).fill(0),
  );
  for (let i = m - 1; i >= 0; i--) {
    const row = lcs[i]!;
    const nextRow = lcs[i + 1]!;
    for (let j = n - 1; j >= 0; j--) {
      if (a[i] === b[j]) row[j] = nextRow[j + 1]! + 1;
      else row[j] = Math.max(nextRow[j]!, row[j + 1]!);
    }
  }

  const out: DiffLine[] = [];
  let i = 0;
  let j = 0;
  while (i < m && j < n) {
    if (a[i] === b[j]) {
      out.push({ op: "context", oldLine: i + 1, newLine: j + 1, text: a[i]! });
      i++;
      j++;
    } else if (lcs[i + 1]![j]! >= lcs[i]![j + 1]!) {
      out.push({ op: "remove", oldLine: i + 1, newLine: null, text: a[i]! });
      i++;
    } else {
      out.push({ op: "add", oldLine: null, newLine: j + 1, text: b[j]! });
      j++;
    }
  }
  while (i < m) {
    out.push({ op: "remove", oldLine: i + 1, newLine: null, text: a[i]! });
    i++;
  }
  while (j < n) {
    out.push({ op: "add", oldLine: null, newLine: j + 1, text: b[j]! });
    j++;
  }
  return out;
}

export function diffStats(lines: DiffLine[]): { added: number; removed: number } {
  let added = 0;
  let removed = 0;
  for (const l of lines) {
    if (l.op === "add") added++;
    else if (l.op === "remove") removed++;
  }
  return { added, removed };
}

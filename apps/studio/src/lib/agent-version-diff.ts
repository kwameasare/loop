const MISSING = Symbol("missing");

type Missing = typeof MISSING;

export type ConfigDiffStatus = "added" | "removed" | "changed";

export interface ConfigDiffRow {
  path: string;
  status: ConfigDiffStatus;
  before: string;
  after: string;
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function sortJson(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sortJson);
  if (!isPlainObject(value)) return value;
  return Object.fromEntries(
    Object.keys(value)
      .sort()
      .map((key) => [key, sortJson(value[key])]),
  );
}

function renderValue(value: unknown | Missing): string {
  if (value === MISSING) return "-";
  if (typeof value === "string") return value;
  if (value === null) return "null";
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return JSON.stringify(sortJson(value), null, 2) ?? "undefined";
}

function sameValue(before: unknown, after: unknown): boolean {
  return JSON.stringify(sortJson(before)) === JSON.stringify(sortJson(after));
}

function walkDiff(
  before: unknown | Missing,
  after: unknown | Missing,
  path: string,
  rows: ConfigDiffRow[],
) {
  if (before !== MISSING && after !== MISSING && sameValue(before, after)) {
    return;
  }
  if (isPlainObject(before) && isPlainObject(after)) {
    const keys = new Set([...Object.keys(before), ...Object.keys(after)]);
    for (const key of [...keys].sort()) {
      const nextPath = path ? `${path}.${key}` : key;
      walkDiff(
        Object.prototype.hasOwnProperty.call(before, key)
          ? before[key]
          : MISSING,
        Object.prototype.hasOwnProperty.call(after, key) ? after[key] : MISSING,
        nextPath,
        rows,
      );
    }
    return;
  }

  const status =
    before === MISSING ? "added" : after === MISSING ? "removed" : "changed";
  rows.push({
    path: path || "$",
    status,
    before: renderValue(before),
    after: renderValue(after),
  });
}

export function diffConfigJson(
  before: Record<string, unknown>,
  after: Record<string, unknown>,
): ConfigDiffRow[] {
  const rows: ConfigDiffRow[] = [];
  walkDiff(before, after, "", rows);
  return rows;
}

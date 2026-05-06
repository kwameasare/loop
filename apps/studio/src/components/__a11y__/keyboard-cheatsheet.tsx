import { KEYBOARD_SHORTCUTS } from "@/lib/a11y";
import { cn } from "@/lib/utils";

const SCOPE_LABELS: Record<(typeof KEYBOARD_SHORTCUTS)[number]["scope"], string> = {
  global: "Global",
  canvas: "Canvas / list view",
  trace: "Trace",
  review: "Review",
};

export interface KeyboardCheatsheetProps {
  className?: string;
}

/**
 * Visible reference of every canonical shortcut (§30.1, §30.2, §30.3).
 * Renders as a sortable definition list keyboard users can scan in one pass.
 */
export function KeyboardCheatsheet({
  className,
}: KeyboardCheatsheetProps): JSX.Element {
  const grouped = new Map<string, typeof KEYBOARD_SHORTCUTS[number][]>();
  for (const shortcut of KEYBOARD_SHORTCUTS) {
    const list = grouped.get(shortcut.scope) ?? [];
    list.push(shortcut);
    grouped.set(shortcut.scope, list);
  }
  return (
    <section
      aria-label="Keyboard shortcuts"
      data-testid="keyboard-cheatsheet"
      className={cn(
        "rounded-md border border-border bg-card p-4 text-sm",
        className,
      )}
    >
      <h2 className="text-base font-semibold">Keyboard shortcuts</h2>
      <p className="mt-1 text-xs text-muted-foreground">
        Every shortcut is reachable without a mouse. Press <kbd>?</kbd> to
        focus this list at any time.
      </p>
      <div className="mt-3 space-y-4">
        {Array.from(grouped.entries()).map(([scope, items]) => (
          <div key={scope} data-testid={`keyboard-scope-${scope}`}>
            <h3 className="text-xs uppercase tracking-wide text-muted-foreground">
              {SCOPE_LABELS[scope as keyof typeof SCOPE_LABELS]}
            </h3>
            <dl className="mt-2 grid grid-cols-[8rem_1fr] gap-x-3 gap-y-1">
              {items.map((s) => (
                <div key={s.id} className="contents">
                  <dt>
                    <kbd
                      data-testid={`shortcut-combo-${s.id}`}
                      className="rounded border border-border bg-muted px-2 py-0.5 font-mono text-xs"
                    >
                      {s.combo}
                    </kbd>
                  </dt>
                  <dd className="text-muted-foreground">
                    {s.description}{" "}
                    <span className="text-[10px] uppercase tracking-wide text-muted-foreground/70">
                      {s.anchor}
                    </span>
                  </dd>
                </div>
              ))}
            </dl>
          </div>
        ))}
      </div>
    </section>
  );
}

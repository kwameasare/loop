"use client";

import type { PresenceStatus, PresenceUser } from "@/lib/collaboration";

interface PresenceBarProps {
  users: readonly PresenceUser[];
}

const STATUS_LABEL: Record<PresenceStatus, string> = {
  active: "active",
  viewing: "viewing",
  idle: "idle",
};

export function PresenceBar(props: PresenceBarProps): JSX.Element {
  const { users } = props;
  return (
    <section
      data-testid="presence-bar"
      aria-label="Active collaborators"
      className="flex flex-wrap items-center gap-2 instrument-panel rounded-xl p-2 text-xs"
    >
      <span className="text-[11px] font-medium text-muted-foreground">
        Live · {users.length}
      </span>
      <ul className="flex flex-wrap items-center gap-2">
        {users.map((u) => (
          <li
            key={u.id}
            data-testid={`presence-user-${u.id}`}
            className="flex items-center gap-2 rounded-full border bg-background px-2 py-0.5"
          >
            <span
              aria-hidden
              className="inline-block h-2 w-2 rounded-full"
              style={{ backgroundColor: u.color }}
            />
            <span className="font-medium">{u.display}</span>
            <span className="text-[11px] text-muted-foreground">
              {STATUS_LABEL[u.status]}
              {u.focus ? ` · ${u.focus}` : ""}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

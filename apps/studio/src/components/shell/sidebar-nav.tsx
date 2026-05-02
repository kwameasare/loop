"use client";

/**
 * S153: Sidebar navigation for the studio app shell.
 *
 * Renders a vertical list of links to the major studio sections. The
 * link to the active route gets ``aria-current="page"`` plus a darker
 * background so users can see where they are at a glance.
 */

import Link from "next/link";
import { usePathname } from "next/navigation";

interface NavItem {
  href: string;
  label: string;
}

export const NAV_ITEMS: readonly NavItem[] = [
  { href: "/agents", label: "Agents" },
  { href: "/evals", label: "Evals" },
  { href: "/inbox", label: "Inbox" },
  { href: "/costs", label: "Costs" },
];

function isActive(current: string | null, href: string): boolean {
  if (!current) return false;
  if (current === href) return true;
  return current.startsWith(`${href}/`);
}

export function SidebarNav() {
  const pathname = usePathname();
  return (
    <nav aria-label="Primary" className="flex flex-col gap-1 p-4">
      <p className="px-2 pb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        Loop
      </p>
      {NAV_ITEMS.map((item) => {
        const active = isActive(pathname, item.href);
        return (
          <Link
            key={item.href}
            href={item.href}
            data-testid={`nav-${item.label.toLowerCase()}`}
            aria-current={active ? "page" : undefined}
            className={
              "rounded-md px-3 py-2 text-sm font-medium transition-colors " +
              (active
                ? "bg-accent text-accent-foreground"
                : "text-muted-foreground hover:bg-accent/50 hover:text-foreground")
            }
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}

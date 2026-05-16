import Link from "next/link";

export interface AgentSectionPlaceholderProps {
  title: string;
  purpose: string;
  requiredObjects: string[];
  primaryHref?: string;
  primaryLabel?: string;
}

export function AgentSectionPlaceholder({
  title,
  purpose,
  requiredObjects,
  primaryHref,
  primaryLabel,
}: AgentSectionPlaceholderProps) {
  return (
    <section
      className="instrument-panel rounded-2xl p-5"
      data-testid="agent-section-placeholder"
      aria-labelledby="agent-section-placeholder-heading"
    >
      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        Agent workbench section
      </p>
      <h2
        id="agent-section-placeholder-heading"
        className="mt-2 text-xl font-semibold"
      >
        {title}
      </h2>
      <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
        {purpose}
      </p>
      <div className="mt-4 rounded-md border bg-background p-3">
        <p className="text-sm font-medium">Required durable objects</p>
        <ul className="mt-2 grid gap-2 text-sm text-muted-foreground sm:grid-cols-2">
          {requiredObjects.map((item) => (
            <li key={item} className="rounded-md border bg-card px-3 py-2">
              {item}
            </li>
          ))}
        </ul>
      </div>
      {primaryHref && primaryLabel ? (
        <Link
          href={primaryHref}
          className="mt-4 inline-flex rounded-md border px-3 py-2 text-sm font-medium hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
        >
          {primaryLabel}
        </Link>
      ) : null}
    </section>
  );
}

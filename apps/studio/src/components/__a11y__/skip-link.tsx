import { cn } from "@/lib/utils";

export interface SkipLinkProps {
  /** ID of the main content landmark to jump to. */
  targetId: string;
  /** Visible label. Localised by the caller. */
  label: string;
  className?: string;
}

/**
 * Visually hidden until focused. Keyboard sweep §30.1: every page surfaces a
 * Skip-to-main-content link as the first focusable element.
 */
export function SkipLink({ targetId, label, className }: SkipLinkProps): JSX.Element {
  return (
    <a
      href={`#${targetId}`}
      data-testid="skip-link"
      className={cn(
        "sr-only focus:not-sr-only focus:fixed focus:left-2 focus:top-2",
        "focus:z-50 focus:rounded-md focus:bg-card focus:px-3 focus:py-2",
        "focus:text-sm focus:text-foreground focus:shadow-md focus:outline focus:outline-2 focus:outline-focus",
        className,
      )}
    >
      {label}
    </a>
  );
}

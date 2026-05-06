import {
  announceStatus,
  STATUS_GLYPHS,
  type StatusVariant,
} from "@/lib/a11y";
import { cn } from "@/lib/utils";

const TONE_CLASSES: Record<StatusGlyphSpecToneKey, string> = {
  ok: "text-success",
  danger: "text-destructive",
  warn: "text-warning",
  info: "text-focus",
  muted: "text-muted-foreground",
};

type StatusGlyphSpecToneKey = (typeof STATUS_GLYPHS)[StatusVariant]["tone"];

export interface StatusGlyphProps {
  variant: StatusVariant;
  label?: string;
  className?: string;
  /** When set, the visible label text will be hidden from sighted users but
   *  remain in the accessible name. The shape glyph is always visible. */
  visualLabel?: boolean;
}

/**
 * Communicates status with shape + label + colour (§30.4). Screen readers
 * read the status label and any optional context.
 */
export function StatusGlyph({
  variant,
  label,
  className,
  visualLabel = true,
}: StatusGlyphProps): JSX.Element {
  const spec = STATUS_GLYPHS[variant];
  const announcement = announceStatus(variant, label);
  return (
    <span
      data-testid={`status-glyph-${variant}`}
      data-status={variant}
      data-stroke={spec.strokePattern}
      className={cn(
        "inline-flex items-center gap-1 text-sm",
        TONE_CLASSES[spec.tone],
        className,
      )}
      role="status"
      aria-label={announcement}
    >
      <span aria-hidden="true" className="font-mono">
        {spec.glyph}
      </span>
      {visualLabel ? (
        <span>{label ?? spec.label}</span>
      ) : (
        <span className="sr-only">{announcement}</span>
      )}
    </span>
  );
}

import enCommon from "@/locales/en/common.json";

export type TargetStateKind =
  | "loading"
  | "empty"
  | "error"
  | "degraded"
  | "stale"
  | "permissionBlocked";

export interface TargetStateCopy {
  eyebrow: string;
  title: string;
  description: string;
  evidenceLabel: string;
  primaryAction: string;
  secondaryAction: string;
  stageLabel: string;
  requestIdLabel: string;
  updatedAtLabel: string;
}

type CopyValues = Record<string, string | number | undefined>;

const targetStateCopy = enCommon.targetStates;
const sectionStateCopy = enCommon.sectionStates;

function interpolate(template: string, values: CopyValues = {}): string {
  return template.replace(/\{\{\s*(\w+)\s*\}\}/g, (_match, key: string) => {
    const value = values[key];
    return value === undefined ? "" : String(value);
  });
}

export function getTargetStateCopy(
  state: TargetStateKind,
  values?: CopyValues,
): TargetStateCopy {
  const copy = targetStateCopy[state];
  return {
    eyebrow: interpolate(copy.eyebrow, values),
    title: interpolate(copy.title, values),
    description: interpolate(copy.description, values),
    evidenceLabel: interpolate(copy.evidenceLabel, values),
    primaryAction: interpolate(copy.primaryAction, values),
    secondaryAction: interpolate(copy.secondaryAction, values),
    stageLabel: interpolate(copy.stageLabel, values),
    requestIdLabel: interpolate(copy.requestIdLabel, values),
    updatedAtLabel: interpolate(copy.updatedAtLabel, values),
  };
}

export function getSectionStateCopy(
  state: TargetStateKind,
  values?: CopyValues,
): TargetStateCopy {
  const copy = sectionStateCopy[state];
  return {
    eyebrow: interpolate(copy.eyebrow, values),
    title: interpolate(copy.title, values),
    description: interpolate(copy.description, values),
    evidenceLabel: interpolate(copy.evidenceLabel, values),
    primaryAction: interpolate(copy.primaryAction, values),
    secondaryAction: interpolate(copy.secondaryAction, values),
    stageLabel: interpolate(copy.stageLabel, values),
    requestIdLabel: interpolate(copy.requestIdLabel, values),
    updatedAtLabel: interpolate(copy.updatedAtLabel, values),
  };
}

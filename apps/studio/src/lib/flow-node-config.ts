import type { FlowNodeType } from "./flow-nodes";

/**
 * Node-config primitives. Each node type owns its own config shape;
 * unrecognised fields are stripped on save.
 */

export interface NodeConfigBase {
  label?: string;
}

export interface MessageNodeConfig extends NodeConfigBase {
  body: string;
}

export interface ConditionNodeConfig extends NodeConfigBase {
  expression: string;
}

export interface AiTaskNodeConfig extends NodeConfigBase {
  prompt: string;
  model: string;
}

export interface HttpNodeConfig extends NodeConfigBase {
  method: "GET" | "POST" | "PUT" | "DELETE";
  url: string;
}

export interface CodeNodeConfig extends NodeConfigBase {
  source: string;
}

export type NodeConfigByType = {
  start: NodeConfigBase;
  message: MessageNodeConfig;
  condition: ConditionNodeConfig;
  "ai-task": AiTaskNodeConfig;
  http: HttpNodeConfig;
  code: CodeNodeConfig;
  end: NodeConfigBase;
};

export type AnyNodeConfig = NodeConfigByType[keyof NodeConfigByType];

export type ValidationErrors = Record<string, string>;

export function defaultConfigFor<T extends FlowNodeType>(
  type: T,
): NodeConfigByType[T] {
  switch (type) {
    case "start":
    case "end":
      return {} as NodeConfigByType[T];
    case "message":
      return { body: "" } as NodeConfigByType[T];
    case "condition":
      return { expression: "" } as NodeConfigByType[T];
    case "ai-task":
      return { prompt: "", model: "gpt-4o-mini" } as NodeConfigByType[T];
    case "http":
      return { method: "GET", url: "" } as NodeConfigByType[T];
    case "code":
      return { source: "" } as NodeConfigByType[T];
    default: {
      const _: never = type;
      throw new Error(`unknown type ${_}`);
    }
  }
}

/**
 * Validate a node's config. Returns a flat ``{field: message}`` map; an
 * empty object means the node is valid.
 */
export function validateNodeConfig(
  type: FlowNodeType,
  config: AnyNodeConfig,
): ValidationErrors {
  const errs: ValidationErrors = {};
  switch (type) {
    case "message": {
      const c = config as MessageNodeConfig;
      if (!c.body || c.body.trim() === "")
        errs.body = "Message body is required.";
      break;
    }
    case "condition": {
      const c = config as ConditionNodeConfig;
      if (!c.expression || c.expression.trim() === "")
        errs.expression = "Expression is required.";
      break;
    }
    case "ai-task": {
      const c = config as AiTaskNodeConfig;
      if (!c.prompt || c.prompt.trim() === "")
        errs.prompt = "Prompt is required.";
      if (!c.model || c.model.trim() === "")
        errs.model = "Model is required.";
      break;
    }
    case "http": {
      const c = config as HttpNodeConfig;
      if (!c.url || c.url.trim() === "") {
        errs.url = "URL is required.";
      } else {
        try {
          // eslint-disable-next-line no-new
          new URL(c.url);
        } catch {
          errs.url = "URL must be a valid absolute URL.";
        }
      }
      break;
    }
    case "code": {
      const c = config as CodeNodeConfig;
      if (!c.source || c.source.trim() === "")
        errs.source = "Code body is required.";
      break;
    }
    default:
      break;
  }
  return errs;
}

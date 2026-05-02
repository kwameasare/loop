/**
 * S471: Flow starter templates — FAQ, support-triage, lead-qual.
 */
import { type FlowEdge } from "@/lib/flow-edges";
import { type FlowNode } from "@/lib/flow-nodes";

export interface FlowTemplate {
  id: string;
  name: string;
  description: string;
  nodes: FlowNode[];
  edges: FlowEdge[];
}

export const FLOW_TEMPLATES: FlowTemplate[] = [
  {
    id: "faq",
    name: "FAQ Bot",
    description:
      "A knowledge-base lookup template: start → AI task (answer from KB) → message → end.",
    nodes: [
      { id: "start-1", type: "start", x: 80, y: 160 },
      { id: "ai-task-1", type: "ai-task", x: 280, y: 160 },
      { id: "message-1", type: "message", x: 480, y: 160 },
      { id: "end-1", type: "end", x: 680, y: 160 },
    ],
    edges: [
      { id: "e_start-1_ai-task-1", source: "start-1", target: "ai-task-1" },
      { id: "e_ai-task-1_message-1", source: "ai-task-1", target: "message-1" },
      { id: "e_message-1_end-1", source: "message-1", target: "end-1" },
    ],
  },
  {
    id: "support-triage",
    name: "Support Triage",
    description:
      "Classify inbound support request then route: start → AI task (classify) → condition → message (escalate / resolve) → end.",
    nodes: [
      { id: "start-1", type: "start", x: 80, y: 200 },
      { id: "ai-task-1", type: "ai-task", x: 280, y: 200 },
      { id: "condition-1", type: "condition", x: 480, y: 200 },
      { id: "message-1", type: "message", x: 680, y: 120 },
      { id: "message-2", type: "message", x: 680, y: 280 },
      { id: "end-1", type: "end", x: 880, y: 200 },
    ],
    edges: [
      { id: "e_start-1_ai-task-1", source: "start-1", target: "ai-task-1" },
      { id: "e_ai-task-1_condition-1", source: "ai-task-1", target: "condition-1" },
      { id: "e_condition-1_message-1", source: "condition-1", target: "message-1" },
      { id: "e_condition-1_message-2", source: "condition-1", target: "message-2" },
      { id: "e_message-1_end-1", source: "message-1", target: "end-1" },
      { id: "e_message-2_end-1", source: "message-2", target: "end-1" },
    ],
  },
  {
    id: "lead-qual",
    name: "Lead Qualification",
    description:
      "Collect lead info then qualify via AI: start → message (ask questions) → AI task (score) → condition → end.",
    nodes: [
      { id: "start-1", type: "start", x: 80, y: 200 },
      { id: "message-1", type: "message", x: 280, y: 200 },
      { id: "ai-task-1", type: "ai-task", x: 480, y: 200 },
      { id: "condition-1", type: "condition", x: 680, y: 200 },
      { id: "end-1", type: "end", x: 880, y: 120 },
      { id: "end-2", type: "end", x: 880, y: 280 },
    ],
    edges: [
      { id: "e_start-1_message-1", source: "start-1", target: "message-1" },
      { id: "e_message-1_ai-task-1", source: "message-1", target: "ai-task-1" },
      { id: "e_ai-task-1_condition-1", source: "ai-task-1", target: "condition-1" },
      { id: "e_condition-1_end-1", source: "condition-1", target: "end-1" },
      { id: "e_condition-1_end-2", source: "condition-1", target: "end-2" },
    ],
  },
];

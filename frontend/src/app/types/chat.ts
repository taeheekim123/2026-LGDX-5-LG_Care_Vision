import type { ChatDeviceOption } from "./device";

export interface Message {
  id: string;
  type: "user" | "bot";
  content: string;
  time: string;
  options?: string[];
  problemOptions?: string[];
  showVideo?: boolean;
  guideButtons?: ("manual" | "ar")[];
  showDoneAsk?: boolean;
  showSchedule?: boolean;
  showServiceSummary?: ServiceInfo;
  showServiceComplete?: boolean;
  modelOptions?: ChatDeviceOption[];
}

export interface ServiceInfo {
  product: string;
  name: string;
  phone: string;
  address: string;
  model: string;
  issue: string;
}

export type ServiceStep = "idle" | "model" | "issue";
export type FlowType = "trouble" | "care" | "service" | null;
export type RecommendedAction = "manual" | "ar" | "video" | "service" | "llm";

export interface ChatContext {
  intent?: Exclude<FlowType, null>;
  productCategory?: string;
  productType?: string;
  deviceId?: string;
  productName?: string;
  model?: string;
  symptom?: string;
  issue?: string;
  recommendedActions?: RecommendedAction[];
}

export interface ScheduleDateOption {
  label: string;
  value: string;
}


import { apiGet, apiPost } from "./client";
import type { ChatGuideOptions } from "../types/chat";

export type CareRiskFactor = {
  factor: string;
  value: number | string | Record<string, number>;
  score_delta: number;
  reason: string;
};

export type CareRiskResponse = {
  care_risk_score: {
    score: number;
    risk_level: "low" | "medium" | "high";
    trigger_reason: string[];
  };
  care_risk_decision: {
    factor_scores: CareRiskFactor[];
  };
};

export type CareRiskLocation = {
  region: string;
  city: string;
  userEmail?: string;
};

export async function evaluateCareRisk(location?: CareRiskLocation): Promise<CareRiskResponse> {
  return apiPost<CareRiskResponse, { user_id: string; device_id: string; procedure_type: string; region?: string; city?: string }>(
    "/v1/care/risk/evaluate",
    {
      user_id: location?.userEmail ?? "u001@careshot.local",
      device_id: "D001",
      procedure_type: "filter_cleaning",
      region: location?.region,
      city: location?.city,
    },
  );
}

export type GuideOptionsRequest = {
  userId?: string;
  deviceId?: string;
  procedureType?: string;
  serviceFlowType?: "self_care" | "self_as";
  languageCode?: string;
};

export async function getGuideOptions(request: GuideOptionsRequest = {}): Promise<ChatGuideOptions> {
  const params = new URLSearchParams({
    user_id: request.userId ?? "U001",
    device_id: request.deviceId ?? "D001",
    procedure_type: request.procedureType ?? "filter_cleaning",
    service_flow_type: request.serviceFlowType ?? "self_care",
    language_code: request.languageCode ?? "en",
  });
  return apiGet<ChatGuideOptions>(`/v1/guides/options?${params.toString()}`);
}

export type CompleteGuidePayload = {
  userId?: string;
  deviceId?: string;
  guideId?: string | number;
  procedureType?: string;
  serviceFlowType?: "self_care" | "self_as";
};

export async function completeGuide(payload: CompleteGuidePayload): Promise<void> {
  const guideId = payload.guideId ?? "1";
  await apiPost<unknown, { user_id: string; device_id: string; procedure_type?: string; service_flow_type: "self_care" | "self_as" }>(
    `/v1/guides/${guideId}/complete`,
    {
      user_id: payload.userId ?? "U001",
      device_id: payload.deviceId ?? "D001",
      procedure_type: payload.procedureType,
      service_flow_type: payload.serviceFlowType ?? "self_care",
    },
  );
}

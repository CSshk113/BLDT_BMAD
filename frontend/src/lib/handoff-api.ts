import { ApiRequestError } from "./criteria-api";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type HandoffCard = {
  id: string;
  application_id: string;
  criteria_version_id: string;
  status: "PROCESSING" | "READY" | "FAILED";
  payload: {
    application: { id: string; candidate_token: string; position_name: string };
    source_document: { artifact_id: string; processing_run_id: string | null; content: string };
    criteria: { version_id: string; position_name: string; items: Array<{ id: string; criterion_text: string; requirement_type: string }> };
    evidence: Array<{ id: string; criterion_item_id: string; criterion_text: string; citation: string; location: string; evidence_status: string; processing_run_id: string | null; source_artifact_id: string | null }>;
    judgments: Record<string, unknown>;
    differences: Array<{ criterion_item_id: string; fields: string[] }>;
    insufficient_evidence: Array<{ criterion_item_id: string; criterion_text: string; question_needed: boolean }>;
    interview_questions: unknown[];
    interview_results: unknown[];
  };
  created_by: string;
  failure_reason: string | null;
  created_at: string;
  updated_at: string;
};

export type HandoffGenerationResponse = { card: HandoffCard; already_exists: boolean };

export class HandoffApiError extends ApiRequestError {
  constructor(status: number) {
    super(status);
    this.name = "HandoffApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers: { "Content-Type": "application/json", ...init?.headers } });
  if (!response.ok) throw new HandoffApiError(response.status);
  return response.json() as Promise<T>;
}

export function generateHandoffCard(versionId: string, applicationId: string, role = "LEAD") {
  return request<HandoffGenerationResponse>(`/api/handoff/generate?criteria_version_id=${encodeURIComponent(versionId)}&application_id=${encodeURIComponent(applicationId)}`, { method: "POST", headers: { "X-Demo-Role": role } });
}

export function loadHandoffCard(cardId: string) {
  return request<HandoffCard>(`/api/handoff/${encodeURIComponent(cardId)}`);
}

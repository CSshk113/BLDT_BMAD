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
    interview_questions: QuestionCandidate[];
    interview_results: InterviewVerification[];
    final_decision: DecisionRecord | null;
    audit_timeline: AuditEvent[];
  };
  created_by: string;
  failure_reason: string | null;
  created_at: string;
  updated_at: string;
};

export type HandoffGenerationResponse = { card: HandoffCard; already_exists: boolean };

export type QuestionCandidate = {
  id: string;
  original_question: string;
  current_question: string;
  reason: string;
  criterion_item_ids: string[];
  evidence_ids: string[];
  question_type: "BEI" | "SJT" | "KNOWLEDGE" | string;
  status: "CANDIDATE" | "SELECTED" | "DELETED";
  created_at: string;
  edit_history: Array<{
    action?: string;
    previous_question?: string;
    new_question?: string;
    actor: string;
    timestamp: string;
    reason: string;
  }>;
};

export type QuestionCandidateListResponse = {
  card_id: string;
  candidates: QuestionCandidate[];
  selected_question_ids: string[];
};

export type InterviewVerification = {
  id: string;
  question_id: string;
  original_question: string;
  current_question: string;
  criterion_item_ids: string[];
  evidence_ids: string[];
  initial_hypothesis: string;
  interview_result: string;
  recorded_by: string;
  recorded_at: string;
  edit_history: Array<Record<string, unknown>>;
};

export type DecisionValue = "채용" | "미채용" | "종료" | "인재풀 등록";

export type DecisionRecord = {
  id: string;
  decision: DecisionValue;
  reason: string;
  actor: string;
  decided_at: string;
  criteria_version_id: string;
  edit_history: Array<Record<string, unknown>>;
};

export type AuditEvent = {
  event_type: string;
  target_id: string;
  actor: string;
  timestamp: string;
  source: string;
  summary: string;
};

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

export function generateQuestionCandidates(cardId: string, role = "LEAD") {
  return request<QuestionCandidateListResponse>(`/api/questions/${encodeURIComponent(cardId)}/generate`, { method: "POST", headers: { "X-Demo-Role": role } });
}

export function loadQuestionCandidates(cardId: string, role = "LEAD", selectedOnly = false) {
  const query = selectedOnly ? "?selected_only=true" : "";
  return request<QuestionCandidateListResponse>(`/api/questions/${encodeURIComponent(cardId)}${query}`, { headers: { "X-Demo-Role": role } });
}

export function editQuestionCandidate(cardId: string, questionId: string, currentQuestion: string, editReason: string, role: "HR" | "HM") {
  return request<QuestionCandidate>(`/api/questions/${encodeURIComponent(cardId)}/${encodeURIComponent(questionId)}`, {
    method: "PATCH",
    headers: { "X-Demo-Role": role },
    body: JSON.stringify({ current_question: currentQuestion, edit_reason: editReason }),
  });
}

export function deleteQuestionCandidate(cardId: string, questionId: string, role: "HR" | "HM") {
  return request<QuestionCandidate>(`/api/questions/${encodeURIComponent(cardId)}/${encodeURIComponent(questionId)}`, { method: "DELETE", headers: { "X-Demo-Role": role } });
}

export function selectQuestionCandidate(cardId: string, questionId: string, selected: boolean, role = "LEAD") {
  return request<QuestionCandidate>(`/api/questions/${encodeURIComponent(cardId)}/${encodeURIComponent(questionId)}/select`, {
    method: "POST",
    headers: { "X-Demo-Role": role },
    body: JSON.stringify({ selected }),
  });
}

export function saveInterviewVerification(cardId: string, questionId: string, interviewResult: string, editReason?: string) {
  return request<HandoffCard>(`/api/handoff/${encodeURIComponent(cardId)}/verifications`, {
    method: "POST",
    headers: { "X-Demo-Role": "LEAD" },
    body: JSON.stringify({ question_id: questionId, interview_result: interviewResult, edit_reason: editReason }),
  });
}

export function saveFinalDecision(cardId: string, decision: DecisionValue, reason: string, editReason?: string) {
  return request<HandoffCard>(`/api/handoff/${encodeURIComponent(cardId)}/decision`, {
    method: "POST",
    headers: { "X-Demo-Role": "LEAD" },
    body: JSON.stringify({ decision, reason, edit_reason: editReason }),
  });
}

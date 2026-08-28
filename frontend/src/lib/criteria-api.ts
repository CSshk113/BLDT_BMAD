import type { CriteriaItem } from "@/components/criteria/CriteriaVersionPanel";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiRequestError extends Error {
  constructor(public readonly status: number) {
    super(`API request failed: ${status}`);
    this.name = "ApiRequestError";
  }
}

export function isNetworkError(error: unknown): boolean {
  return error instanceof TypeError;
}

export type CriteriaVersionStatus = "DRAFT" | "APPROVED" | "ARCHIVED";

export type ApiCriteriaVersion = {
  id: string;
  position_name: string;
  status: CriteriaVersionStatus;
  items: Array<{ id: string; criterion_text: string; requirement_type: "필수" | "우대" }>;
  updated_at: string;
  approved_at?: string | null;
  approved_by?: ReviewerRole | null;
};

export type ApiPreview = {
  mappings: Array<{
    application_id: string;
    applicant_label: string;
    criterion_item_id: string;
    citation: string;
    location: string;
    evidence_status: string;
    mapping_status: "RECEIVED" | "COMPLETED" | "INVALIDATED";
  }>;
};

export type ReviewerRole = "HR" | "HM";
export type ReviewStatus =
  | "FULFILLED"
  | "PARTIALLY_FULFILLED"
  | "UNFULFILLED"
  | "UNVERIFIABLE";

export type ReviewLog = {
  id: string;
  criteria_version_id: string;
  application_id: string;
  criterion_item_id: string;
  reviewer_role: ReviewerRole;
  review_scope?: "CALIBRATION" | "OFFICIAL";
  status: ReviewStatus;
  reason_text: string;
  source_location: string;
  citation?: string;
  edit_history?: Array<Record<string, unknown>>;
  created_at: string;
  updated_at: string;
};

export type ReviewRow = {
  criterion_item_id: string;
  criterion_text: string;
  requirement_type: "필수" | "우대";
  conflict_status: "OPEN" | "RESOLVED" | "PENDING" | "NONE";
  differences: string[];
  hr_review: ReviewLog | null;
  hm_review: ReviewLog | null;
  resolution?: ConflictResolution | null;
};

export type CalibrationSample = {
  application_id: string;
  candidate_token: string;
  position_name: string;
  source: string;
  excerpt: string;
  source_location: string;
};

export type ReviewMatrix = {
  criteria_version_id: string;
  application_id: string;
  application_summary?: CalibrationSample | null;
  rows: ReviewRow[];
  open_conflict_count: number;
};

export type ReviewInput = {
  criterion_item_id: string;
  status: ReviewStatus;
  reason_text: string;
  source_location: string;
};

export type ReviewSubmission = {
  application_id: string;
  reviewer_role: ReviewerRole;
  reviews: ReviewInput[];
};

export type JudgmentLog = ReviewLog & { review_scope: "OFFICIAL"; citation: string; edit_history: Array<Record<string, unknown>> };
export type DocumentJudgment = {
  reviewer_role: ReviewerRole;
  verdict: string;
  edit_history: Array<Record<string, unknown>>;
  created_at: string;
  updated_at: string;
};
export type JudgmentRow = {
  criterion_item_id: string;
  criterion_text: string;
  requirement_type: "필수" | "우대";
  differences: string[];
  hr_review: JudgmentLog | null;
  hm_review: JudgmentLog | null;
};
export type JudgmentMatrix = {
  criteria_version_id: string;
  application_id: string;
  hr_document_judgment: DocumentJudgment | null;
  hm_document_judgment: DocumentJudgment | null;
  rows: JudgmentRow[];
};
export type JudgmentInput = {
  criterion_item_id: string;
  status: ReviewStatus;
  reason_text: string;
  citation?: string;
  source_location?: string;
  edit_reason?: string;
};
export type JudgmentSubmission = {
  application_id: string;
  reviewer_role: ReviewerRole;
  document_verdict?: string;
  document_edit_reason?: string;
  reviews: JudgmentInput[];
};

export type ConflictResolution = {
  id: string;
  criteria_version_id: string;
  application_id: string;
  criterion_item_id: string;
  status: "RESOLVED";
  resolved_by: ReviewerRole;
  resolved_at: string;
  resolution_reason: string;
};

export type CriteriaApprovalResult = {
  version: ApiCriteriaVersion;
  criteria_version_id: string;
  approved_by: ReviewerRole;
  approved_at: string;
};

export type HandoffResult = {
  status: "ready";
  handoff_unlocked: boolean;
  criteria_version_id: string;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) throw new ApiRequestError(response.status);
  return response.json() as Promise<T>;
}

export function toUiItems(version: ApiCriteriaVersion): CriteriaItem[] {
  return version.items.map((item) => ({
    id: item.id,
    text: item.criterion_text,
    type: item.requirement_type,
  }));
}

export async function loadCriteria(versionId: string) {
  const version = await request<ApiCriteriaVersion>(`/api/criteria/${versionId}`);
  return { version, items: toUiItems(version) };
}

export async function loadPreview(versionId: string) {
  return request<ApiPreview>(`/api/criteria/${versionId}/preview`);
}

export async function saveDraft(versionId: string, items: CriteriaItem[]) {
  return request<{ version: ApiCriteriaVersion; invalidated_mapping_count: number; rerun_required: boolean }>(
    `/api/criteria/${versionId}`,
    { method: "PATCH", body: JSON.stringify({ items: items.map((item) => ({ criterion_text: item.text })) }) },
  );
}

export async function createDraft(versionId: string) {
  return request<ApiCriteriaVersion>(`/api/criteria/${versionId}/versions`, { method: "POST" });
}

const demoReview = (
  versionId: string,
  applicationId: string,
  itemId: string,
  role: ReviewerRole,
  status: ReviewStatus,
  reason: string,
  location: string,
): ReviewLog => ({
  id: `demo-${role.toLowerCase()}-${itemId}`,
  criteria_version_id: versionId,
  application_id: applicationId,
  criterion_item_id: itemId,
  reviewer_role: role,
  status,
  reason_text: reason,
  source_location: location,
  created_at: "2026-08-27T07:00:00Z",
  updated_at: "2026-08-27T07:00:00Z",
});

export function fallbackReviewMatrix(versionId: string, items: CriteriaItem[] = []): ReviewMatrix {
  const fallbackItems = items.length > 0 ? items : [
    { id: "item-1", text: "콜드 아웃바운드 영업 경험", type: "필수" as const },
    { id: "item-2", text: "B2B 세일즈 파이프라인 운영 경험", type: "필수" as const },
    { id: "item-3", text: "CRM 또는 세일즈 데이터 기반 성과 관리", type: "우대" as const },
  ];
  const reviewSeeds: Array<[ReviewerRole, ReviewStatus, string, string]> = [
    ["HR", "FULFILLED", "아웃바운드 영업 경험을 확인했습니다.", "p.2 · 경력기술서"],
    ["HM", "PARTIALLY_FULFILLED", "경험은 보이지만 콜드 아웃바운드 범위가 불명확합니다.", "p.2 · 경력기술서"],
    ["HR", "UNVERIFIABLE", "파이프라인 운영 방식에 대한 직접 근거가 없습니다.", "p.3 · 프로젝트"],
    ["HR", "PARTIALLY_FULFILLED", "CRM 활용 경험은 있으나 성과 수치가 부족합니다.", "p.3 · 프로젝트"],
    ["HM", "UNFULFILLED", "CRM 기반 성과 관리 근거를 확인하지 못했습니다.", "p.3 · 프로젝트"],
  ];
  const reviews: ReviewLog[] = reviewSeeds.flatMap(([role, status, reason, location], index) => {
    const item = fallbackItems[Math.floor(index / 2) === 0 ? 0 : Math.floor(index / 2) === 1 ? 1 : 2];
    return item ? [demoReview(versionId, "APPS-2", item.id, role, status, reason, location)] : [];
  });
  const rows = fallbackItems.map((item) => {
    const hrReview = reviews.find((review) => review.criterion_item_id === item.id && review.reviewer_role === "HR") ?? null;
    const hmReview = reviews.find((review) => review.criterion_item_id === item.id && review.reviewer_role === "HM") ?? null;
    const differences = hrReview && hmReview
      ? [
          ...(hrReview.status !== hmReview.status ? ["상태"] : []),
          ...(normalizeSourceLocation(hrReview.source_location) !== normalizeSourceLocation(hmReview.source_location) ? ["원문 위치"] : []),
        ]
      : [];
    return { criterion_item_id: item.id, criterion_text: item.text, requirement_type: item.type, conflict_status: differences.length > 0 ? "OPEN" as const : !hrReview || !hmReview ? "PENDING" as const : "NONE" as const, differences, hr_review: hrReview, hm_review: hmReview };
  });
  return {
    criteria_version_id: versionId,
    application_id: "APPS-2",
    application_summary: {
      application_id: "APPS-2",
      candidate_token: "후보081",
      position_name: "B2B 영업 매니저 5년 이상 ver.4",
      source: "원티드",
      excerpt: '“신규 고객 30개사를 직접 발굴하고 콜드 아웃바운드로 미팅을 만들었습니다.”',
      source_location: "p.2 · 경력기술서",
    },
    rows,
    open_conflict_count: rows.filter((row) => row.conflict_status === "OPEN").length,
  };
}

export function normalizeSourceLocation(value: string): string {
  const normalized = value
    .normalize("NFKC")
    .toLowerCase()
    .trim()
    .replace(/(?:p|page)\.?\s*(\d+)\s*[-~–—]\s*(\d+)/g, "page-range:$1:$2")
    .replace(/(\d+)\s*[-~–—]\s*(\d+)\s*페이지/g, "page-range:$1:$2")
    .replace(/(?:p|page)\.?\s*(\d+)/g, "page:$1")
    .replace(/(\d+)\s*페이지|페이지\s*(\d+)/g, (_match, before, after) => `page:${before ?? after}`)
  const tokens = normalized.match(/page-range:\d+:\d+|page:\d+|[가-힣A-Za-z0-9+#.]+/g) ?? [];
  return tokens.sort().join("|");
}

export async function loadReviewMatrix(versionId: string, items: CriteriaItem[] = []) {
  try {
    const matrix = await request<ReviewMatrix>(`/api/criteria/${versionId}/conflicts?application_id=APPS-2`);
    if (!Array.isArray(matrix.rows)) throw new Error("Invalid review matrix");
    return matrix;
  } catch (error) {
    if (isNetworkError(error)) return fallbackReviewMatrix(versionId, items);
    throw error;
  }
}

export async function saveReview(versionId: string, payload: ReviewSubmission) {
  return request<ReviewMatrix>(`/api/criteria/${versionId}/reviews`, {
    method: "POST",
    headers: { "X-Demo-Role": payload.reviewer_role },
    body: JSON.stringify(payload),
  });
}

export async function loadJudgmentMatrix(versionId: string, applicationId = "APPS-2") {
  return request<JudgmentMatrix>(
    `/api/criteria/${encodeURIComponent(versionId)}/judgments?application_id=${encodeURIComponent(applicationId)}`,
  );
}

export async function saveJudgments(versionId: string, payload: JudgmentSubmission) {
  return request<JudgmentMatrix>(`/api/criteria/${encodeURIComponent(versionId)}/judgments`, {
    method: "POST",
    headers: { "X-Demo-Role": payload.reviewer_role },
    body: JSON.stringify(payload),
  });
}

export async function resolveConflict(versionId: string, payload: { application_id: string; criterion_item_id: string; resolution_reason: string }) {
  return request<ReviewMatrix>(`/api/criteria/${versionId}/conflicts`, {
    method: "POST",
    headers: { "X-Demo-Role": "HR" },
    body: JSON.stringify(payload),
  });
}

export async function approveCriteria(versionId: string, role: ReviewerRole = "HR") {
  return request<CriteriaApprovalResult>(`/api/criteria/${versionId}/approve`, {
    method: "POST",
    headers: { "X-Demo-Role": role },
  });
}

export async function generateHandoff(versionId: string) {
  return request<HandoffResult>(`/api/handoff/generate?criteria_version_id=${encodeURIComponent(versionId)}`, {
    method: "POST",
  });
}

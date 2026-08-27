export type EvidenceStatus = "충족" | "부분 충족" | "미충족" | "확인 불가";
export type EvidenceLocationKind = "EXACT" | "FALLBACK" | "NONE";
export type MappingStatus = "RECEIVED" | "COMPLETED" | "INVALIDATED";

export type MappingResult = {
  id: string;
  application_id: string;
  criteria_version_id: string;
  processing_run_id: string | null;
  source_artifact_id: string | null;
  applicant_label: string;
  criterion_item_id: string;
  criterion_text: string;
  requirement_type: string;
  citation: string;
  location: string;
  location_kind: EvidenceLocationKind;
  evidence_status: EvidenceStatus;
  mapping_status: MappingStatus;
};

export type MappingResponse = {
  application_id: string;
  criteria_version_id: string;
  criteria_status: "DRAFT" | "APPROVED" | "ARCHIVED";
  is_preview: boolean;
  processing_run_id: string;
  source_artifact_id: string;
  mappings: MappingResult[];
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class MappingApiError extends Error {
  constructor(public readonly status: number) {
    super(`Mapping API request failed: ${status}`);
    this.name = "MappingApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) throw new MappingApiError(response.status);
  return response.json() as Promise<T>;
}

export function createMappings(applicationId: string, criteriaVersionId?: string) {
  return request<MappingResponse>("/api/mappings", {
    method: "POST",
    body: JSON.stringify({ application_id: applicationId, criteria_version_id: criteriaVersionId || undefined }),
  });
}

export function getMappings(applicationId: string, criteriaVersionId?: string, runId?: string) {
  const params = new URLSearchParams();
  if (criteriaVersionId) params.set("criteria_version_id", criteriaVersionId);
  if (runId) params.set("run_id", runId);
  const query = params.toString();
  return request<MappingResponse>(`/api/mappings/${encodeURIComponent(applicationId)}${query ? `?${query}` : ""}`);
}

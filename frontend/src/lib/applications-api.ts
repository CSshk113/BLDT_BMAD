export type ProcessingStatus = "RECEIVED" | "PARSING" | "MAPPING" | "COMPLETED" | "FAILED";
export type ApplicationSource = "UPLOAD" | "SAMPLE" | "LEDGER_ONLY";
export type ArtifactType = "ORIGINAL_PDF" | "LLAMAPARSE_MARKDOWN" | "NORMALIZED_MARKDOWN";

export type LedgerMetadata = {
  channel?: string | null;
  position?: string | null;
  applied_at?: string | null;
  overall_status?: string | null;
  rejection_reason?: string | null;
  sample_stage?: string | null;
  sample_name?: string | null;
  sample_file_available?: boolean;
};

export type ApplicationSummary = {
  id: string;
  candidate_token: string;
  position_name: string;
  criteria_version_id: string | null;
  source_type: ApplicationSource | null;
  list_status: string;
  processing_status: ProcessingStatus | null;
  current_step: string | null;
  failed_step: string | null;
  failure_reason: string | null;
  last_successful_run_id: string | null;
  last_successful_artifact_types: ArtifactType[];
  ledger_metadata: LedgerMetadata;
  created_at: string | null;
  updated_at: string | null;
};

export type ApplicationArtifact = {
  id: string;
  application_id: string;
  processing_run_id: string | null;
  artifact_type: ArtifactType;
  original_filename: string;
  mime_type: string;
  is_current: boolean;
  created_at: string;
};

export type ProcessingRunEvent = { status: ProcessingStatus; step: string; occurred_at: string; detail: string | null };
export type ProcessingRun = {
  id: string;
  application_id: string;
  criteria_version_id: string;
  status: ProcessingStatus;
  current_step: string;
  parser_model: string;
  received_at: string;
  parsing_started_at: string | null;
  mapping_started_at: string | null;
  completed_at: string | null;
  failed_at: string | null;
  failure_step: string | null;
  failure_reason: string | null;
  created_at: string;
  updated_at: string;
  events: ProcessingRunEvent[];
};

export type ApplicationDetail = ApplicationSummary & {
  artifacts: ApplicationArtifact[];
  processing_runs: ProcessingRun[];
  can_review: boolean;
};

export type ApplicationDocument = {
  application_id: string;
  criteria_version_id: string;
  processing_run_id: string;
  artifact_id: string;
  source_type: "NORMALIZED_MARKDOWN";
  content: string;
};

export type ApplicationsList = {
  items: ApplicationSummary[];
  total_ledger_count: number;
  sample_count: number;
  uploaded_count: number;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApplicationApiError extends Error {
  constructor(public readonly status: number) {
    super(`Application API request failed: ${status}`);
    this.name = "ApplicationApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) throw new ApplicationApiError(response.status);
  return response.json() as Promise<T>;
}

export function listApplications() {
  return request<ApplicationsList>("/api/applications");
}

export function getApplication(applicationId: string) {
  return request<ApplicationDetail>(`/api/applications/${encodeURIComponent(applicationId)}`);
}

export function getApplicationDocument(applicationId: string, runId?: string) {
  const query = runId ? `?run_id=${encodeURIComponent(runId)}` : "";
  return request<ApplicationDocument>(`/api/applications/${encodeURIComponent(applicationId)}/document${query}`);
}

export function uploadApplication(input: { file: File; candidateToken: string; positionName: string; criteriaVersionId: string }) {
  const form = new FormData();
  form.append("file", input.file);
  form.append("candidate_token", input.candidateToken);
  form.append("position_name", input.positionName);
  form.append("criteria_version_id", input.criteriaVersionId);
  return request<ApplicationDetail>("/api/applications", { method: "POST", body: form });
}

export function reprocessApplication(applicationId: string) {
  return request<ApplicationDetail>(`/api/applications/${encodeURIComponent(applicationId)}/process`, { method: "POST" });
}

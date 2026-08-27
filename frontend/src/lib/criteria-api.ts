import type { CriteriaItem } from "@/components/criteria/CriteriaVersionPanel";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type ApiCriteriaVersion = {
  id: string;
  position_name: string;
  status: "DRAFT" | "APPROVED" | "ARCHIVED";
  items: Array<{ id: string; criterion_text: string; requirement_type: "필수" | "우대" }>;
  updated_at: string;
};

export type ApiPreview = {
  mappings: Array<{ mapping_status: "RECEIVED" | "COMPLETED" | "INVALIDATED" }>;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) throw new Error(`API request failed: ${response.status}`);
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

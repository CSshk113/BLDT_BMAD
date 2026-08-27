import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ApplicationsPage from "./page";
import { getApplication, listApplications } from "@/lib/applications-api";

vi.mock("@/lib/applications-api", () => ({
  getApplication: vi.fn(),
  listApplications: vi.fn(),
  reprocessApplication: vi.fn(),
  uploadApplication: vi.fn(),
}));

const item = {
  id: "APPS-28",
  candidate_token: "후보068",
  position_name: "B2B 영업 매니저 (5년 이상)",
  criteria_version_id: "cv-b2b-sales-v4",
  source_type: "SAMPLE" as const,
  list_status: "처리 완료",
  processing_status: "COMPLETED" as const,
  current_step: "COMPLETED",
  failed_step: null,
  failure_reason: null,
  last_successful_run_id: "run-1",
  last_successful_artifact_types: ["ORIGINAL_PDF" as const],
  ledger_metadata: { channel: "그룹바이", applied_at: "2026-06-02" },
  created_at: null,
  updated_at: null,
};

describe("applications page", () => {
  it("loads the catalog and selected application detail", async () => {
    vi.mocked(listApplications).mockResolvedValue({ items: [item], total_ledger_count: 178, sample_count: 20, uploaded_count: 0 });
    vi.mocked(getApplication).mockResolvedValue({ ...item, artifacts: [], processing_runs: [], can_review: true });

    render(<ApplicationsPage />);

    await waitFor(() => expect(screen.getAllByText("후보068 · B2B 영업 매니저 (5년 이상)").length).toBeGreaterThan(0));
    expect(screen.getByText("원장 178건")).toBeInTheDocument();
    expect(screen.getByText("처리 완료")).toBeInTheDocument();
  });
});

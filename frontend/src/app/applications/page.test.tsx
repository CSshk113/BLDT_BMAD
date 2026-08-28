import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ApplicationsPage from "./page";
import { getApplication, listApplications, reprocessApplication, type ApplicationDetail } from "@/lib/applications-api";

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

const originalPdf = (applicationId: string) => ({
  id: "artifact-original",
  application_id: applicationId,
  processing_run_id: null,
  artifact_type: "ORIGINAL_PDF" as const,
  original_filename: "candidate.pdf",
  mime_type: "application/pdf",
  is_current: true,
  created_at: "2026-08-28T00:00:00Z",
});

const detail = (overrides: Partial<ApplicationDetail> = {}): ApplicationDetail => {
  const application = { ...item, ...overrides };
  return {
    ...application,
    artifacts: overrides.artifacts ?? [originalPdf(application.id)],
    processing_runs: overrides.processing_runs ?? [],
    can_review: overrides.can_review ?? false,
  };
};

const mockPageLoad = (application: ApplicationDetail) => {
  vi.mocked(listApplications).mockResolvedValue({ items: [application], total_ledger_count: 178, sample_count: 20, uploaded_count: 0 });
  vi.mocked(getApplication).mockResolvedValue(application);
};

describe("applications page", () => {
  beforeEach(() => vi.clearAllMocks());

  it("loads the catalog and selected application detail", async () => {
    vi.mocked(listApplications).mockResolvedValue({ items: [item], total_ledger_count: 178, sample_count: 20, uploaded_count: 0 });
    vi.mocked(getApplication).mockResolvedValue({ ...item, artifacts: [], processing_runs: [], can_review: true });

    render(<ApplicationsPage />);

    await waitFor(() => expect(screen.getAllByText("후보068 · B2B 영업 매니저 (5년 이상)").length).toBeGreaterThan(0));
    expect(screen.getByText("원장 178건")).toBeInTheDocument();
    expect(screen.getByText("매핑 포함 처리 완료")).toBeInTheDocument();
  });

  it("starts processing an unprocessed sample with its current original PDF", async () => {
    const application = detail({ id: "APPS-179", processing_status: null, current_step: null, last_successful_run_id: null, last_successful_artifact_types: [] });
    const completed = detail({ id: "APPS-179", processing_status: "COMPLETED", current_step: "COMPLETED", last_successful_run_id: "run-179", last_successful_artifact_types: ["ORIGINAL_PDF", "LLAMAPARSE_MARKDOWN", "NORMALIZED_MARKDOWN"], can_review: true });
    vi.mocked(listApplications)
      .mockResolvedValueOnce({ items: [application], total_ledger_count: 178, sample_count: 20, uploaded_count: 0 })
      .mockResolvedValue({ items: [completed], total_ledger_count: 178, sample_count: 20, uploaded_count: 0 });
    vi.mocked(getApplication).mockResolvedValueOnce(application).mockResolvedValue(completed);
    vi.mocked(reprocessApplication).mockResolvedValue(completed);

    render(<ApplicationsPage />);

    const startButton = await screen.findByRole("button", { name: "처리 시작" });
    fireEvent.click(startButton);

    await waitFor(() => expect(reprocessApplication).toHaveBeenCalledWith("APPS-179"));
    await waitFor(() => expect(vi.mocked(listApplications).mock.calls.length).toBeGreaterThanOrEqual(2));
    await waitFor(() => expect(screen.queryByRole("button", { name: "처리 시작" })).not.toBeInTheDocument());
    expect(screen.getByRole("link", { name: "원문 근거 검토" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "다시 처리" })).not.toBeInTheDocument();
  });

  it("keeps retry for a failed application with its current original PDF", async () => {
    mockPageLoad(detail({ processing_status: "FAILED", current_step: "PARSING", failed_step: "PARSING", failure_reason: "파서 실패" }));

    render(<ApplicationsPage />);

    expect(await screen.findByRole("button", { name: "다시 처리" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "처리 시작" })).not.toBeInTheDocument();
  });

  it("shows a failed first sample processing result without a completed-review link", async () => {
    const initial = detail({ id: "APPS-179", processing_status: null, current_step: null, last_successful_run_id: null, last_successful_artifact_types: [] });
    const failed = detail({ id: "APPS-179", processing_status: "FAILED", current_step: "PARSING", failed_step: "PARSING", failure_reason: "테스트 파서 실패", last_successful_run_id: null, last_successful_artifact_types: [] });
    vi.mocked(listApplications)
      .mockResolvedValueOnce({ items: [initial], total_ledger_count: 178, sample_count: 20, uploaded_count: 0 })
      .mockResolvedValue({ items: [failed], total_ledger_count: 178, sample_count: 20, uploaded_count: 0 });
    vi.mocked(getApplication).mockResolvedValueOnce(initial).mockResolvedValue(failed);
    vi.mocked(reprocessApplication).mockResolvedValue(failed);

    render(<ApplicationsPage />);

    fireEvent.click(await screen.findByRole("button", { name: "처리 시작" }));

    expect(await screen.findByText("처리 실패 · PARSING")).toBeInTheDocument();
    expect(screen.getByText("테스트 파서 실패")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "다시 처리" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "원문 근거 검토" })).not.toBeInTheDocument();
  });

  it.each([
    ["ledger-only candidate with a current original PDF", detail({ source_type: "LEDGER_ONLY", processing_status: null, current_step: null })],
    ["sample without an original PDF", detail({ processing_status: null, current_step: null, artifacts: [] })],
  ])("does not offer processing for a %s", async (_scenario, application) => {
    mockPageLoad(application);

    render(<ApplicationsPage />);

    await screen.findByText(`${application.candidate_token} · ${application.position_name}`);
    expect(screen.queryByRole("button", { name: "처리 시작" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "다시 처리" })).not.toBeInTheDocument();
  });

  it("disables the start action while the request is pending to prevent duplicate requests", async () => {
    const application = detail({ id: "APPS-179", processing_status: null, current_step: null, last_successful_run_id: null, last_successful_artifact_types: [] });
    mockPageLoad(application);
    let resolveRequest: (value: ApplicationDetail) => void = () => undefined;
    vi.mocked(reprocessApplication).mockImplementation(() => new Promise((resolve) => { resolveRequest = resolve; }));

    render(<ApplicationsPage />);

    fireEvent.click(await screen.findByRole("button", { name: "처리 시작" }));
    const processingButton = await screen.findByRole("button", { name: "처리 중…" });
    expect(processingButton).toBeDisabled();
    fireEvent.click(processingButton);
    expect(reprocessApplication).toHaveBeenCalledTimes(1);
    expect(reprocessApplication).toHaveBeenCalledWith("APPS-179");

    resolveRequest(application);
    await waitFor(() => expect(screen.queryByRole("button", { name: "처리 중…" })).not.toBeInTheDocument());
  });
});

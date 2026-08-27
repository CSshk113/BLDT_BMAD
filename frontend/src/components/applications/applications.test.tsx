import { fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { describe, expect, it, vi } from "vitest";
import { ProcessingList } from "./ProcessingList";
import { UploadForm } from "./UploadForm";

describe("application intake", () => {
  it("rejects a non-PDF before calling the upload callback", async () => {
    const onUploaded = vi.fn();
    render(<UploadForm onUploaded={onUploaded} />);
    const file = new File(["not a pdf"], "resume.docx", { type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" });

    fireEvent.change(screen.getByLabelText("지원서 PDF"), { target: { files: [file] } });
    fireEvent.submit(screen.getByRole("button", { name: "PDF 접수 및 처리" }).closest("form")!);

    expect(await screen.findByText("PDF 파일만 업로드할 수 있습니다.")).toBeInTheDocument();
    expect(onUploaded).not.toHaveBeenCalled();
  });

  it("labels a ledger-only candidate without a PDF as unavailable for processing", () => {
    render(<ProcessingList items={[{
      id: "APPS-1",
      candidate_token: "후보001",
      position_name: "B2B 영업 매니저 (5년 이상)",
      criteria_version_id: "cv-b2b-sales-v4",
      source_type: "LEDGER_ONLY",
      list_status: "원장 데이터만 있음",
      processing_status: null,
      current_step: null,
      failed_step: null,
      failure_reason: null,
      last_successful_run_id: null,
      last_successful_artifact_types: [],
      ledger_metadata: { channel: "원티드", applied_at: "2026-06-18" },
      created_at: null,
      updated_at: null,
    }]} selectedId="" onSelect={vi.fn()} />);

    expect(screen.getByText("원장 데이터만 있음")).toBeInTheDocument();
  });
});

import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MappingResults } from "./MappingResults";

describe("criteria mapping results", () => {
  it("labels Draft results and shows source-first fallback evidence", () => {
    render(<MappingResults result={{
      application_id: "UPLOAD-1",
      criteria_version_id: "cv-b2b-sales-v4",
      criteria_status: "DRAFT",
      is_preview: true,
      processing_run_id: "run-1",
      source_artifact_id: "artifact-1",
      mappings: [{
        id: "mapping-1",
        application_id: "UPLOAD-1",
        criteria_version_id: "cv-b2b-sales-v4",
        processing_run_id: "run-1",
        source_artifact_id: "artifact-1",
        applicant_label: "후보-upload-001",
        criterion_item_id: "item-1",
        criterion_text: "콜드 아웃바운드 영업 경험",
        requirement_type: "필수",
        citation: "실제 원문 인용구",
        location: "문맥 보기 fallback · 문단 2",
        location_kind: "FALLBACK",
        evidence_status: "부분 충족",
        mapping_status: "COMPLETED",
      }],
    }} />);

    expect(screen.getByText("Draft 미리보기")).toBeInTheDocument();
    expect(screen.getByText(/문맥 보기 fallback/)).toBeInTheDocument();
    expect(screen.getByText(/실제 원문 인용구/)).toBeInTheDocument();
  });
});

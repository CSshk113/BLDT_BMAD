import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { EvidenceSplitView } from "./EvidenceSplitView";

const document = {
  application_id: "UPLOAD-1",
  criteria_version_id: "cv-b2b-sales-v4",
  processing_run_id: "run-1",
  artifact_id: "artifact-1",
  source_type: "NORMALIZED_MARKDOWN" as const,
  content: "# 후보\n\n정확한 원문 문장입니다.",
};

const result = {
  application_id: "UPLOAD-1",
  criteria_version_id: "cv-b2b-sales-v4",
  criteria_status: "APPROVED" as const,
  is_preview: false,
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
    criterion_text: "영업 경험",
    requirement_type: "필수",
    citation: "정확한 원문 문장입니다.",
    location: "문단 2",
    location_kind: "FALLBACK" as const,
    evidence_status: "충족" as const,
    mapping_status: "COMPLETED" as const,
  }],
};

describe("evidence split view", () => {
  it("searches and visibly highlights the exact citation after keyboard activation", () => {
    render(<EvidenceSplitView document={document} result={result} />);

    fireEvent.keyDown(screen.getByRole("button", { name: /원문 인용구 선택/ }), { key: "Enter" });

    expect(screen.getByText("정확한 원문 문장입니다.", { selector: "mark" })).toBeInTheDocument();
    expect(screen.getByText(/원문에서 인용구를 찾았습니다/)).toBeInTheDocument();
    expect(screen.getByText(/문맥 보기 fallback/)).toBeInTheDocument();
  });

  it("shows match failure without highlighting unrelated source text", () => {
    const view = render(<EvidenceSplitView document={document} result={{ ...result, mappings: [{ ...result.mappings[0], citation: "원문에 없는 인용구" }] }} />);

    fireEvent.click(screen.getByRole("button", { name: /원문 인용구 선택/ }));

    expect(screen.getByText("원문 일치 실패", { selector: "[data-slot='alert-title']" })).toBeInTheDocument();
    expect(screen.getByText(/원문 일치 실패입니다/)).toBeInTheDocument();
    expect(view.container.querySelector("mark[data-active-citation='true']")).toBeNull();
  });

  it("shows an empty evidence state when mappings are unavailable", () => {
    render(<EvidenceSplitView document={document} result={{ ...result, mappings: [] }} />);

    expect(screen.getByText("검토 가능한 근거가 없습니다.")).toBeInTheDocument();
  });
});

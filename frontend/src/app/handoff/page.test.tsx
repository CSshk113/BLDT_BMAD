import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { describe, expect, it, vi } from "vitest";
import HandoffPage from "./page";
import {
  generateHandoffCard,
  generateQuestionCandidates,
  loadQuestionCandidates,
  selectQuestionCandidate,
  type HandoffCard,
  type QuestionCandidate,
} from "@/lib/handoff-api";

vi.mock("@/lib/handoff-api", () => ({
  deleteQuestionCandidate: vi.fn(),
  editQuestionCandidate: vi.fn(),
  generateHandoffCard: vi.fn(),
  generateQuestionCandidates: vi.fn(),
  loadQuestionCandidates: vi.fn(),
  selectQuestionCandidate: vi.fn(),
}));

const card = {
  id: "handoff-1",
  application_id: "APPS-2",
  criteria_version_id: "approved-v1",
  status: "READY",
  payload: {
    application: { id: "APPS-2", candidate_token: "후보081", position_name: "B2B 영업 매니저" },
    source_document: { artifact_id: "artifact-1", processing_run_id: "run-1", content: "콜드 아웃바운드 경험" },
    criteria: { version_id: "approved-v1", position_name: "B2B 영업 매니저", items: [] },
    evidence: [{ id: "mapping-1", criterion_item_id: "item-1", criterion_text: "콜드 아웃바운드", citation: "콜드 아웃바운드 경험", location: "p.1", evidence_status: "충족", processing_run_id: "run-1", source_artifact_id: "artifact-1" }],
    judgments: { rows: [] },
    differences: [],
    insufficient_evidence: [],
    interview_questions: [],
    interview_results: [],
  },
  created_by: "LEAD",
  failure_reason: null,
  created_at: "2026-08-28T00:00:00Z",
  updated_at: "2026-08-28T00:00:00Z",
} as HandoffCard;

const candidate = {
  id: "question-1",
  original_question: "신규 고객 경험을 말씀해 주세요.",
  current_question: "연이 없는 신규 고객을 발굴한 경험을 말씀해 주세요.",
  reason: "콜드 아웃바운드 경험 확인",
  criterion_item_ids: ["item-1"],
  evidence_ids: ["mapping-1"],
  question_type: "BEI",
  status: "CANDIDATE",
  created_at: "2026-08-28T00:00:00Z",
  edit_history: [],
} as QuestionCandidate;

describe("handoff question workflow", () => {
  it("loads candidates and sends the LEAD selection request", async () => {
    vi.mocked(generateHandoffCard).mockResolvedValue({ card, already_exists: false });
    vi.mocked(loadQuestionCandidates).mockResolvedValue({ card_id: card.id, candidates: [candidate], selected_question_ids: [] });
    vi.mocked(selectQuestionCandidate).mockResolvedValue({ ...candidate, status: "SELECTED" });

    render(<HandoffPage />);
    fireEvent.click(screen.getByRole("button", { name: "핸드오프 생성" }));

    expect(await screen.findByText(candidate.current_question)).toBeInTheDocument();
    expect(screen.getByText("콜드 아웃바운드 경험 (p.1)")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "인터뷰에 선택" }));

    await waitFor(() => expect(selectQuestionCandidate).toHaveBeenCalledWith(card.id, candidate.id, true, "LEAD"));
  });
});

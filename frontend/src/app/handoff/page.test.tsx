import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { describe, expect, it, vi } from "vitest";
import HandoffPage from "./page";
import {
  generateHandoffCard,
  generateQuestionCandidates,
  loadQuestionCandidates,
  saveFinalDecision,
  saveInterviewVerification,
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
  saveFinalDecision: vi.fn(),
  saveInterviewVerification: vi.fn(),
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
    final_decision: null,
    audit_timeline: [],
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

  it("records a selected question result and a human final decision", async () => {
    const selectedCandidate = { ...candidate, status: "SELECTED" } as QuestionCandidate;
    const verification = {
      id: "verification-1",
      question_id: selectedCandidate.id,
      original_question: selectedCandidate.original_question,
      current_question: selectedCandidate.current_question,
      criterion_item_ids: selectedCandidate.criterion_item_ids,
      evidence_ids: selectedCandidate.evidence_ids,
      initial_hypothesis: selectedCandidate.reason,
      interview_result: "실제 면접에서 신규 고객 발굴 과정을 확인했습니다.",
      recorded_by: "LEAD",
      recorded_at: "2026-08-28T00:00:00Z",
      edit_history: [],
    };
    const verifiedCard = { ...card, payload: { ...card.payload, interview_results: [verification], final_decision: null, audit_timeline: [] } } as HandoffCard;
    const decidedCard = { ...verifiedCard, payload: { ...verifiedCard.payload, final_decision: { id: "decision-1", decision: "채용", reason: "검증 결과가 충분합니다.", actor: "LEAD", decided_at: "2026-08-28T00:00:00Z", criteria_version_id: card.criteria_version_id, edit_history: [] } } } as HandoffCard;
    vi.mocked(generateHandoffCard).mockResolvedValue({ card, already_exists: false });
    vi.mocked(loadQuestionCandidates).mockResolvedValue({ card_id: card.id, candidates: [selectedCandidate], selected_question_ids: [selectedCandidate.id] });
    vi.mocked(saveInterviewVerification).mockResolvedValue(verifiedCard);
    vi.mocked(saveFinalDecision).mockResolvedValue(decidedCard);

    render(<HandoffPage />);
    fireEvent.click(screen.getByRole("button", { name: "핸드오프 생성" }));
    expect((await screen.findAllByText(selectedCandidate.current_question)).length).toBeGreaterThan(0);

    fireEvent.change(screen.getByLabelText("면접 결과 question-1"), { target: { value: verification.interview_result } });
    fireEvent.click(screen.getByRole("button", { name: "검증 결과 저장" }));
    await waitFor(() => expect(saveInterviewVerification).toHaveBeenCalledWith(card.id, selectedCandidate.id, verification.interview_result, undefined));
    expect(screen.getByDisplayValue(verification.interview_result)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("최종 결정값"), { target: { value: "채용" } });
    fireEvent.change(screen.getByLabelText("결정 사유"), { target: { value: "검증 결과가 충분합니다." } });
    fireEvent.click(screen.getByRole("button", { name: "최종 결정 저장" }));
    await waitFor(() => expect(saveFinalDecision).toHaveBeenCalledWith(card.id, "채용", "검증 결과가 충분합니다.", undefined));
    expect(await screen.findByText("저장된 결정: 채용")).toBeInTheDocument();
  });
});

"use client";

import { useEffect, useState } from "react";
import React from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import {
  deleteQuestionCandidate,
  editQuestionCandidate,
  generateHandoffCard,
  generateQuestionCandidates,
  loadQuestionCandidates,
  saveFinalDecision,
  saveInterviewVerification,
  selectQuestionCandidate,
  type DecisionValue,
  type HandoffCard,
  type QuestionCandidate,
} from "@/lib/handoff-api";

type Judgment = {
  status?: string;
  reason_text?: string | null;
  citation?: string | null;
  source_location?: string | null;
};

type JudgmentRow = {
  criterion_item_id: string;
  criterion_text: string;
  differences: string[];
  hr_review?: Judgment | null;
  hm_review?: Judgment | null;
};

export default function HandoffPage() {
  const [applicationId, setApplicationId] = useState("APPS-2");
  const [versionId, setVersionId] = useState("cv-b2b-sales-v4");
  const [card, setCard] = useState<HandoffCard | null>(null);
  const [candidates, setCandidates] = useState<QuestionCandidate[]>([]);
  const [role, setRole] = useState<"LEAD" | "HR" | "HM">("LEAD");
  const [selectedOnly, setSelectedOnly] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState("");
  const [editReason, setEditReason] = useState("");
  const [questionBusy, setQuestionBusy] = useState(false);
  const [verificationDrafts, setVerificationDrafts] = useState<Record<string, string>>({});
  const [verificationReasons, setVerificationReasons] = useState<Record<string, string>>({});
  const [decisionValue, setDecisionValue] = useState<DecisionValue | "">("");
  const [decisionReason, setDecisionReason] = useState("");
  const [decisionEditReason, setDecisionEditReason] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setApplicationId(params.get("application_id") ?? "APPS-2");
    setVersionId(params.get("criteria_version_id") ?? "cv-b2b-sales-v4");
  }, []);

  const hydrateInterviewState = (nextCard: HandoffCard) => {
    setCard(nextCard);
    setVerificationDrafts(Object.fromEntries((nextCard.payload.interview_results ?? []).map((item) => [item.question_id, item.interview_result])));
    setVerificationReasons({});
    const decision = nextCard.payload.final_decision;
    setDecisionValue(decision?.decision ?? "");
    setDecisionReason(decision?.reason ?? "");
    setDecisionEditReason("");
  };

  const create = async () => {
    const nextApplicationId = applicationId.trim();
    const nextVersionId = versionId.trim();
    if (!nextApplicationId || !nextVersionId) {
      setCard(null);
      setError("지원서 ID와 기준 버전 ID를 입력하세요.");
      return;
    }

    setError("");
    try {
      const nextCard = (await generateHandoffCard(nextVersionId, nextApplicationId)).card;
      hydrateInterviewState(nextCard);
      setCandidates((await loadQuestionCandidates(nextCard.id, role)).candidates);
    } catch {
      setCard(null);
      setCandidates([]);
      setError("핸드오프 생성 조건을 확인하세요. 승인 기준·완료 매핑·원문·HR/HM 판단 로그가 모두 필요합니다.");
    }
  };

  const refreshQuestions = async (cardId: string, onlySelected = selectedOnly) => {
    setCandidates((await loadQuestionCandidates(cardId, role, onlySelected)).candidates);
  };

  const changeRole = (nextRole: "LEAD" | "HR" | "HM") => {
    setRole(nextRole);
    setEditingId(null);
    setEditReason("");
  };

  const createQuestions = async () => {
    if (!card) return;
    setQuestionBusy(true);
    setError("");
    try {
      await generateQuestionCandidates(card.id, role);
      await refreshQuestions(card.id);
    } catch {
      setError("질문 후보를 만들 수 없습니다. 승인된 READY 카드와 서버 LLM 설정을 확인한 뒤 다시 시도하세요.");
    } finally {
      setQuestionBusy(false);
    }
  };

  const beginEdit = (candidate: QuestionCandidate) => {
    setEditingId(candidate.id);
    setEditText(candidate.current_question);
    setEditReason("");
  };

  const saveEdit = async () => {
    if (!card || !editingId || role === "LEAD") return;
    if (!editText.trim() || !editReason.trim()) {
      setError("수정 질문과 변경 사유를 입력하세요.");
      return;
    }
    setQuestionBusy(true);
    try {
      await editQuestionCandidate(card.id, editingId, editText, editReason, role);
      setError("");
      setEditingId(null);
      await refreshQuestions(card.id);
    } catch {
      setError("질문 수정이 거부되었습니다. 구체성·근거 연결·공정성 규칙을 확인하세요.");
    } finally {
      setQuestionBusy(false);
    }
  };

  const removeCandidate = async (questionId: string) => {
    if (!card || role === "LEAD") return;
    setQuestionBusy(true);
    try {
      await deleteQuestionCandidate(card.id, questionId, role);
      setError("");
      await refreshQuestions(card.id);
    } catch {
      setError("질문 후보를 삭제할 수 없습니다.");
    } finally {
      setQuestionBusy(false);
    }
  };

  const toggleSelection = async (candidate: QuestionCandidate) => {
    if (!card || role !== "LEAD") return;
    setQuestionBusy(true);
    try {
      await selectQuestionCandidate(card.id, candidate.id, candidate.status !== "SELECTED", role);
      setError("");
      await refreshQuestions(card.id);
    } catch {
      setError("질문 선택 상태를 변경할 수 없습니다.");
    } finally {
      setQuestionBusy(false);
    }
  };

  const saveVerification = async (candidate: QuestionCandidate) => {
    if (!card || role !== "LEAD") return;
    const interviewResult = (verificationDrafts[candidate.id] ?? "").trim();
    const existing = card.payload.interview_results.find((item) => item.question_id === candidate.id);
    const editReason = (verificationReasons[candidate.id] ?? "").trim();
    if (!interviewResult || (existing && !editReason)) {
      setError(existing ? "면접 결과와 변경 사유를 입력하세요." : "면접에서 확인된 결과를 입력하세요.");
      return;
    }
    setQuestionBusy(true);
    try {
      const nextCard = await saveInterviewVerification(card.id, candidate.id, interviewResult, editReason || undefined);
      hydrateInterviewState(nextCard);
      setError("");
    } catch {
      setError("면접 검증 결과를 저장할 수 없습니다. 선택된 질문과 카드 상태를 확인하세요.");
    } finally {
      setQuestionBusy(false);
    }
  };

  const saveDecision = async () => {
    if (!card || role !== "LEAD") return;
    if (!decisionValue || !decisionReason.trim() || (card.payload.final_decision && !decisionEditReason.trim())) {
      setError(card.payload.final_decision ? "결정값·결정 사유·변경 사유를 입력하세요." : "결정값과 결정 사유를 입력하세요.");
      return;
    }
    setQuestionBusy(true);
    try {
      const nextCard = await saveFinalDecision(card.id, decisionValue, decisionReason, decisionEditReason || undefined);
      hydrateInterviewState(nextCard);
      setError("");
    } catch {
      setError("최종 결정을 저장할 수 없습니다. 모든 선택 질문의 면접 검증 결과를 먼저 기록하세요.");
    } finally {
      setQuestionBusy(false);
    }
  };

  const judgmentRows = card
    ? (((card.payload.judgments as { rows?: JudgmentRow[] }).rows ?? []))
    : [];

  return (
    <main className="mx-auto grid max-w-7xl gap-6 p-6">
      <header>
        <p className="text-xs font-semibold tracking-[0.18em] text-muted-foreground">HANDOFF CARD · STORY 3.4</p>
        <h1 className="text-3xl font-semibold tracking-tight">현업 핸드오프 카드</h1>
        <p className="mt-2 text-sm text-muted-foreground">양쪽 판단과 원문 근거에서 면접 검증과 사람의 최종 결정까지 한 장의 JSON 카드로 연결합니다.</p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>카드 생성</CardTitle>
          <CardDescription>승인된 기준과 처리 완료된 지원서만 공식 카드로 만들 수 있습니다.</CardDescription>
        </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-[1fr_1fr_auto_auto] md:items-end">
            <label className="grid gap-2 text-sm font-medium">
            지원서 ID
            <input className="h-10 rounded-md border bg-background px-3" value={applicationId} onChange={(event) => setApplicationId(event.target.value)} />
          </label>
          <label className="grid gap-2 text-sm font-medium">
            기준 버전 ID
            <input className="h-10 rounded-md border bg-background px-3" value={versionId} onChange={(event) => setVersionId(event.target.value)} />
            </label>
            <label className="grid gap-2 text-sm font-medium">
              현재 역할
              <select className="h-10 rounded-md border bg-background px-3" value={role} onChange={(event) => changeRole(event.target.value as "LEAD" | "HR" | "HM")}>
                <option value="LEAD">LEAD · 선택</option>
                <option value="HR">HR · 수정/삭제</option>
                <option value="HM">HM · 수정/삭제</option>
              </select>
            </label>
            <Button type="button" onClick={create}>핸드오프 생성</Button>
        </CardContent>
      </Card>

      {error && <Alert variant="destructive"><AlertTitle>카드를 만들 수 없습니다</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>}

      {card && (
        <section className="grid gap-4" aria-label="핸드오프 카드">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={card.status === "READY" ? "default" : "destructive"}>{card.status}</Badge>
            <Badge variant="outline">{card.payload.application.candidate_token} · {card.application_id}</Badge>
            <span className="text-xs text-muted-foreground">생성자 {card.created_by} · {new Date(card.created_at).toLocaleString("ko-KR")}</span>
          </div>

          <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
            <Card>
              <CardHeader>
                <CardTitle>지원서 원문</CardTitle>
                <CardDescription>산출물 {card.payload.source_document.artifact_id} · 실행 {card.payload.source_document.processing_run_id ?? "없음"}</CardDescription>
              </CardHeader>
              <CardContent>
                <pre className="max-h-[32rem] overflow-y-auto whitespace-pre-wrap break-words font-sans text-sm leading-7">{card.payload.source_document.content}</pre>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>기준·근거</CardTitle>
                <CardDescription>{card.payload.criteria.position_name} · {card.criteria_version_id}</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-3">
                {card.payload.evidence.map((item) => (
                  <div key={item.criterion_item_id} className="rounded-md border p-3">
                    <p className="text-sm font-medium">{item.criterion_text} · {item.evidence_status}</p>
                    {item.citation && <blockquote className="mt-2 border-l-2 pl-3 text-sm">“{item.citation}”</blockquote>}
                    <p className="mt-1 text-xs text-muted-foreground">{item.location} · 매핑 {item.id} · 실행 {item.processing_run_id ?? "없음"} · 산출물 {item.source_artifact_id ?? "없음"}</p>
                  </div>
                ))}
                {card.payload.insufficient_evidence.length > 0 && <Alert><AlertTitle>근거 부족 · 미검증 질문 필요</AlertTitle><AlertDescription>{card.payload.insufficient_evidence.map((item) => item.criterion_text).join(", ")}</AlertDescription></Alert>}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>HR·HM 판단 차이</CardTitle>
              <CardDescription>대표 결론 없이 양쪽 판단을 보존합니다.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-3">
              <div className="rounded-md border p-3 text-sm">
                <p className="font-medium">구조화된 차이</p>
                {card.payload.differences.length ? <ul className="mt-2 list-disc pl-5">{card.payload.differences.map((item) => <li key={item.criterion_item_id}>{item.criterion_item_id}: {item.fields.join(" · ")}</li>)}</ul> : <p className="mt-2 text-muted-foreground">차이가 없습니다.</p>}
              </div>
              {judgmentRows.map((row) => (
                <div className="rounded-md border p-3 text-sm" key={row.criterion_item_id}>
                  <p className="font-medium">{row.criterion_text}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{row.differences.length ? `차이: ${row.differences.join(" · ")}` : "판단 일치"}</p>
                  <div className="mt-3 grid gap-3 md:grid-cols-2">
                    {[{ label: "HR 스크리닝", review: row.hr_review }, { label: "HM 서류 심사", review: row.hm_review }].map(({ label, review }) => (
                      <div className="rounded-md bg-muted/40 p-3" key={label}>
                        <p className="font-medium">{label}</p>
                        <pre className="mt-2 whitespace-pre-wrap text-xs">{JSON.stringify(review ?? "미입력", null, 2)}</pre>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <CardTitle>인터뷰 질문 후보</CardTitle>
                  <CardDescription>카드의 근거와 관련 영업 question-bank 실제 사용 이력으로 만든 후보입니다. AI가 최종 결정을 내리지 않습니다.</CardDescription>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <label className="flex items-center gap-2 text-sm">
                    <input type="checkbox" checked={selectedOnly} onChange={async (event) => { const value = event.target.checked; setSelectedOnly(value); if (card) await refreshQuestions(card.id, value); }} />
                    선택된 질문만
                  </label>
                  {role === "LEAD" && <Button type="button" onClick={createQuestions} disabled={questionBusy}>{questionBusy ? "생성 중…" : "질문 후보 생성"}</Button>}
                </div>
              </div>
            </CardHeader>
            <CardContent className="grid gap-3">
              {candidates.length === 0 && <p className="text-sm text-muted-foreground">표시할 질문 후보가 없습니다. 생성 버튼으로 후보를 준비하세요.</p>}
              {candidates.map((candidate) => (
                <div className="rounded-md border p-4" key={candidate.id}>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant={candidate.status === "SELECTED" ? "default" : "outline"}>{candidate.status}</Badge>
                      <Badge variant="secondary">{candidate.question_type}</Badge>
                      <span className="text-xs text-muted-foreground">생성 {new Date(candidate.created_at).toLocaleString("ko-KR")}</span>
                    </div>
                    <div className="flex gap-2">
                      {role === "LEAD" && <Button type="button" variant={candidate.status === "SELECTED" ? "default" : "outline"} onClick={() => toggleSelection(candidate)} disabled={questionBusy}>{candidate.status === "SELECTED" ? "선택 해제" : "인터뷰에 선택"}</Button>}
                      {role !== "LEAD" && <><Button type="button" variant="outline" onClick={() => beginEdit(candidate)} disabled={questionBusy}>수정</Button><Button type="button" variant="destructive" onClick={() => removeCandidate(candidate.id)} disabled={questionBusy}>삭제</Button></>}
                    </div>
                  </div>
                  {editingId === candidate.id ? (
                    <div className="mt-3 grid gap-2">
                      <Textarea value={editText} onChange={(event) => setEditText(event.target.value)} aria-label="수정할 질문" />
                      <Textarea value={editReason} onChange={(event) => setEditReason(event.target.value)} placeholder="변경 사유" aria-label="변경 사유" />
                      <div className="flex gap-2"><Button type="button" onClick={saveEdit} disabled={questionBusy}>수정 저장</Button><Button type="button" variant="ghost" onClick={() => setEditingId(null)}>취소</Button></div>
                    </div>
                  ) : (
                    <>
                      <p className="mt-3 font-medium">{candidate.current_question}</p>
                      {candidate.original_question !== candidate.current_question && <p className="mt-2 text-xs text-muted-foreground">원질문: {candidate.original_question}</p>}
                    </>
                  )}
                  <div className="mt-3 grid gap-1 text-xs text-muted-foreground md:grid-cols-3">
                    <span>질문 이유: {candidate.reason}</span>
                    <span>연결 기준: {candidate.criterion_item_ids.join(", ")}</span>
                    <span>참조 근거: {candidate.evidence_ids.map((evidenceId) => { const evidence = card.payload.evidence.find((item) => item.id === evidenceId); return <span key={evidenceId} className="mr-2 inline-block">{evidence ? `${evidence.citation} (${evidence.location})` : evidenceId}</span>; })}</span>
                  </div>
                  {candidate.edit_history.length > 0 && <p className="mt-2 text-xs text-muted-foreground">수정 이력 {candidate.edit_history.length}건 · 마지막 사유: {candidate.edit_history.at(-1)?.reason}</p>}
                </div>
              ))}
              {candidates.some((candidate) => candidate.status === "SELECTED") && <Alert><AlertTitle>인터뷰 사용 목록</AlertTitle><AlertDescription>{candidates.filter((candidate) => candidate.status === "SELECTED").map((candidate) => candidate.current_question).join(" · ")}</AlertDescription></Alert>}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>면접 검증 비교</CardTitle>
              <CardDescription>서류 단계의 초기 가설과 LEAD가 기록한 실제 면접 결과를 분리해 보존합니다.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4">
              {candidates.filter((candidate) => candidate.status === "SELECTED").length === 0 && <p className="text-sm text-muted-foreground">먼저 인터뷰에 사용할 질문을 선택하세요.</p>}
              {candidates.filter((candidate) => candidate.status === "SELECTED").map((candidate) => {
                const verification = (card.payload.interview_results ?? []).find((item) => item.question_id === candidate.id);
                return (
                  <div className="grid gap-3 rounded-md border p-4" key={candidate.id}>
                    <div>
                      <Badge variant="outline">선택 질문</Badge>
                      <p className="mt-2 font-medium">{candidate.current_question}</p>
                    </div>
                    <div className="grid gap-3 md:grid-cols-2">
                      <div className="rounded-md bg-muted/40 p-3">
                        <p className="text-sm font-medium">서류 초기 가설</p>
                        <p className="mt-2 whitespace-pre-wrap text-sm">{verification?.initial_hypothesis ?? candidate.reason}</p>
                        <p className="mt-2 text-xs text-muted-foreground">질문 이유·근거 부족·검토자 우려에서 생성된 참고 가설이며 수정되지 않습니다.</p>
                      </div>
                      <div className="grid gap-2">
                        <label className="text-sm font-medium" htmlFor={`verification-${candidate.id}`}>실제 면접 결과</label>
                        <Textarea id={`verification-${candidate.id}`} aria-label={`면접 결과 ${candidate.id}`} disabled={role !== "LEAD" || questionBusy} value={verificationDrafts[candidate.id] ?? ""} onChange={(event) => setVerificationDrafts((current) => ({ ...current, [candidate.id]: event.target.value }))} placeholder="면접에서 확인한 사실·행동·결과를 기록하세요." />
                        {verification && <Textarea aria-label={`검증 결과 변경 사유 ${candidate.id}`} disabled={role !== "LEAD" || questionBusy} value={verificationReasons[candidate.id] ?? ""} onChange={(event) => setVerificationReasons((current) => ({ ...current, [candidate.id]: event.target.value }))} placeholder="기존 결과를 수정할 때 변경 사유" />}
                        {role === "LEAD" && <Button type="button" onClick={() => saveVerification(candidate)} disabled={questionBusy}>{verification ? "검증 결과 수정" : "검증 결과 저장"}</Button>}
                        {verification && <><p className="text-xs text-muted-foreground">기록자 {verification.recorded_by} · {new Date(verification.recorded_at).toLocaleString("ko-KR")} · 수정 이력 {verification.edit_history.length}건</p>{verification.edit_history.map((entry, index) => <p className="text-xs text-muted-foreground" key={`${verification.id}-edit-${index}`}>이전 결과: {String(entry.previous_result ?? "-")} → 변경: {String(entry.new_result ?? "-")} · {String(entry.actor ?? "-")} · {String(entry.timestamp ?? "-")} · 사유: {String(entry.reason ?? "-")}</p>)}</>}
                      </div>
                    </div>
                    <p className="text-xs text-muted-foreground">연결 기준 {candidate.criterion_item_ids.join(", ")} · 참조 근거 {candidate.evidence_ids.join(", ")}</p>
                  </div>
                );
              })}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>사람의 최종 결정</CardTitle>
              <CardDescription>AI가 결정하지 않습니다. 모든 선택 질문의 검증 결과를 확인한 LEAD가 직접 저장합니다.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-3">
              <label className="grid gap-2 text-sm font-medium" htmlFor="final-decision">최종 결정값
                <select id="final-decision" aria-label="최종 결정값" className="h-10 rounded-md border bg-background px-3" disabled={role !== "LEAD" || questionBusy} value={decisionValue} onChange={(event) => setDecisionValue(event.target.value as DecisionValue | "")}>
                  <option value="">결정값 선택</option>
                  <option value="채용">채용</option>
                  <option value="미채용">미채용</option>
                  <option value="종료">종료</option>
                  <option value="인재풀 등록">인재풀 등록</option>
                </select>
              </label>
              <label className="grid gap-2 text-sm font-medium" htmlFor="decision-reason">결정 사유
                <Textarea id="decision-reason" aria-label="결정 사유" disabled={role !== "LEAD" || questionBusy} value={decisionReason} onChange={(event) => setDecisionReason(event.target.value)} placeholder="면접 검증 결과를 바탕으로 사람이 판단한 이유를 입력하세요." />
              </label>
              {card.payload.final_decision && <label className="grid gap-2 text-sm font-medium" htmlFor="decision-edit-reason">결정 변경 사유
                <Textarea id="decision-edit-reason" aria-label="결정 변경 사유" disabled={role !== "LEAD" || questionBusy} value={decisionEditReason} onChange={(event) => setDecisionEditReason(event.target.value)} placeholder="기존 결정을 수정한 이유" />
              </label>}
              {role === "LEAD" && <Button type="button" onClick={saveDecision} disabled={questionBusy}>{card.payload.final_decision ? "최종 결정 수정" : "최종 결정 저장"}</Button>}
              {card.payload.final_decision && <div className="rounded-md border bg-muted/40 p-3 text-sm"><p className="font-medium">저장된 결정: {card.payload.final_decision.decision}</p><p className="mt-1">{card.payload.final_decision.reason}</p><p className="mt-1 text-xs text-muted-foreground">결정자 {card.payload.final_decision.actor} · {new Date(card.payload.final_decision.decided_at).toLocaleString("ko-KR")} · 기준 {card.payload.final_decision.criteria_version_id}</p>{card.payload.final_decision.edit_history.map((entry, index) => <p className="mt-1 text-xs text-muted-foreground" key={`decision-edit-${index}`}>이전 결정: {String((entry.previous_value as { decision?: string })?.decision ?? "-")} → 변경: {String((entry.new_value as { decision?: string })?.decision ?? "-")} · {String(entry.actor ?? "-")} · {String(entry.timestamp ?? "-")} · 사유: {String(entry.reason ?? "-")}</p>)}</div>}
              {(card.payload.audit_timeline ?? []).length > 0 && <div className="rounded-md border p-3"><p className="text-sm font-medium">감사 타임라인</p><ol className="mt-2 grid gap-1 text-xs text-muted-foreground">{(card.payload.audit_timeline ?? []).map((event, index) => <li key={`${event.timestamp}-${index}`}>{new Date(event.timestamp).toLocaleString("ko-KR")} · {event.summary} · 대상 {event.target_id} · {event.actor} · {event.source}</li>)}</ol></div>}
            </CardContent>
          </Card>
        </section>
      )}
    </main>
  );
}

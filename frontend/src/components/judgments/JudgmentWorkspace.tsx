"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { getMappings, type MappingResponse } from "@/lib/mapping-api";
import { loadJudgmentMatrix, saveJudgments, type JudgmentMatrix, type ReviewStatus, type ReviewerRole } from "@/lib/criteria-api";

const STATUS_LABELS: Record<ReviewStatus, string> = {
  FULFILLED: "충족",
  PARTIALLY_FULFILLED: "부분 충족",
  UNFULFILLED: "미충족",
  UNVERIFIABLE: "확인 불가",
};
const STATUS_OPTIONS = Object.entries(STATUS_LABELS) as Array<[ReviewStatus, string]>;
const HR_VERDICTS = ["불합격 - 허수 지원", "불합격 - 경력/역량 부족", "불합격 - 회사/지원자 FIT", "스크리닝 통과"];
const HM_VERDICTS = ["불합격 - 허수 지원", "불합격 - 경력/역량 부족", "불합격 - 회사/지원자 FIT", "불합격 - 기타", "합격 - 필수 역량 충족", "합격 - 회사/지원자 FIT", "합격 - 필수 역량 미충족이나 면접 진행 필요", "합격 - 기타"];

function toStatus(value: string, citation: string): ReviewStatus {
  if (value === "충족") return "FULFILLED";
  if (value === "부분 충족") return "PARTIALLY_FULFILLED";
  if (value === "미충족") return "UNFULFILLED";
  return citation ? "PARTIALLY_FULFILLED" : "UNVERIFIABLE";
}

export function JudgmentWorkspace({ versionId, applicationId }: { versionId: string; applicationId: string }) {
  const [matrix, setMatrix] = useState<JudgmentMatrix | null>(null);
  const [mappings, setMappings] = useState<MappingResponse | null>(null);
  const [role, setRole] = useState<ReviewerRole>("HR");
  const [selectedId, setSelectedId] = useState("");
  const [status, setStatus] = useState<ReviewStatus>("UNVERIFIABLE");
  const [reason, setReason] = useState("");
  const [citation, setCitation] = useState("");
  const [location, setLocation] = useState("");
  const [verdict, setVerdict] = useState("");
  const [editReason, setEditReason] = useState("검토자가 판단 내용을 수정함");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const selectedRow = useMemo(() => matrix?.rows.find((row) => row.criterion_item_id === selectedId) ?? null, [matrix, selectedId]);
  const selectedMapping = mappings?.mappings.find((mapping) => mapping.criterion_item_id === selectedId) ?? null;

  useEffect(() => {
    Promise.all([loadJudgmentMatrix(versionId, applicationId), getMappings(applicationId, versionId)])
      .then(([nextMatrix, nextMappings]) => {
        setMatrix(nextMatrix); setMappings(nextMappings); setSelectedId(nextMatrix.rows[0]?.criterion_item_id ?? "");
      })
      .catch(() => setError("승인된 기준과 처리 완료 매핑을 확인한 뒤 판단 로그를 열어주세요."));
  }, [applicationId, versionId]);

  useEffect(() => {
    if (!selectedRow) return;
    const existing = role === "HR" ? selectedRow.hr_review : selectedRow.hm_review;
    setStatus(existing?.status ?? toStatus(selectedMapping?.evidence_status ?? "확인 불가", selectedMapping?.citation ?? ""));
    setReason(existing?.reason_text ?? "");
    setCitation(existing?.citation ?? selectedMapping?.citation ?? "");
    setLocation(existing?.source_location ?? selectedMapping?.location ?? "");
    const document = role === "HR" ? matrix?.hr_document_judgment : matrix?.hm_document_judgment;
    setVerdict(document?.verdict ?? "");
  }, [role, selectedRow, selectedMapping, matrix]);

  const save = async () => {
    if (!selectedId || !reason.trim()) { setError("판단 사유를 입력하세요."); return; }
    setError(""); setMessage("");
    try {
      const updated = await saveJudgments(versionId, { application_id: applicationId, reviewer_role: role, document_verdict: verdict || undefined, document_edit_reason: editReason, reviews: [{ criterion_item_id: selectedId, status, reason_text: reason, citation, source_location: location, edit_reason: editReason }] });
      setMatrix(updated); setMessage(`${role} 판단 로그를 저장했습니다. 양쪽 판단은 자동으로 통합되지 않습니다.`);
    } catch { setError("판단 로그 저장에 실패했습니다. 인용구가 선택된 매핑과 일치하는지 확인하세요."); }
  };

  if (error && !matrix) return <Alert variant="destructive"><AlertTitle>공식 판단을 열 수 없습니다</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>;
  if (!matrix) return <p className="rounded-md border p-4 text-sm text-muted-foreground">판단 로그를 불러오는 중입니다…</p>;
  const verdictOptions = role === "HR" ? HR_VERDICTS : HM_VERDICTS;
  // The handoff API gates on complete HR/HM Item-level official logs. The
  // Document-level verdict is optional while reviewers enter per-criterion
  // evidence, so it must not hide the next-step navigation here.
  const canContinue = Boolean(matrix.rows.length > 0 && matrix.rows.every((row) => row.hr_review && row.hm_review));
  return <section className="grid gap-4" aria-label="HR과 HM 공식 판단 로그">
    {message && <Alert><AlertTitle>저장 완료</AlertTitle><AlertDescription>{message}</AlertDescription></Alert>}
    {error && <Alert variant="destructive"><AlertTitle>입력 확인</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>}
    <div className="flex flex-wrap items-center gap-2"><Badge>승인 기준 {versionId}</Badge><Badge variant="outline">지원서 {applicationId}</Badge><span className="text-sm text-muted-foreground">Item 상태와 Document 판정은 별도입니다.</span></div>
    <Card><CardHeader><CardTitle>검토자 선택</CardTitle><CardDescription>현재 역할의 로그만 수정할 수 있고, 상대 역할의 로그는 읽기 전용입니다.</CardDescription></CardHeader><CardContent className="flex gap-2"><Button type="button" variant={role === "HR" ? "default" : "outline"} onClick={() => setRole("HR")}>HR 스크리닝</Button><Button type="button" variant={role === "HM" ? "default" : "outline"} onClick={() => setRole("HM")}>HM 서류 심사</Button></CardContent></Card>
    <div className="grid gap-3 md:grid-cols-2"><Card><CardHeader className="pb-3"><CardTitle className="text-base">HR 스크리닝 판정</CardTitle></CardHeader><CardContent className="text-sm">{matrix.hr_document_judgment?.verdict ?? "미입력"}</CardContent></Card><Card><CardHeader className="pb-3"><CardTitle className="text-base">HM 서류 전형 판정</CardTitle></CardHeader><CardContent className="text-sm">{matrix.hm_document_judgment?.verdict ?? "미입력"}</CardContent></Card></div>
    <div className="grid gap-4 lg:grid-cols-[0.8fr_1.2fr]">
      <Card><CardHeader><CardTitle>기준별 판단</CardTitle></CardHeader><CardContent className="grid gap-2">{matrix.rows.map((row) => <button type="button" key={row.criterion_item_id} className={`rounded-md border p-3 text-left ${row.criterion_item_id === selectedId ? "border-primary bg-primary/5" : ""}`} onClick={() => setSelectedId(row.criterion_item_id)}><span className="text-sm font-medium">{row.criterion_text}</span><span className="mt-1 block text-xs text-muted-foreground">{row.differences.length ? `의견 차이 ${row.differences.join("·")}` : row.hr_review && row.hm_review ? "양쪽 판단 일치" : "검토 입력 대기"}</span></button>)}</CardContent></Card>
      <Card><CardHeader><CardTitle>{role} 판단 입력</CardTitle><CardDescription>선택된 매핑의 인용구와 위치를 그대로 확인하고 저장합니다.</CardDescription></CardHeader><CardContent className="grid gap-4">
        <label className="grid gap-2 text-sm font-medium">Item 상태<select className="h-10 rounded-md border bg-background px-3" value={status} onChange={(event) => setStatus(event.target.value as ReviewStatus)}>{STATUS_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
        <label className="grid gap-2 text-sm font-medium">판단 사유<Textarea value={reason} onChange={(event) => setReason(event.target.value)} placeholder="원문 근거를 바탕으로 판단한 이유" /></label>
        <label className="grid gap-2 text-sm font-medium">참조 인용구<Textarea value={citation} onChange={(event) => setCitation(event.target.value)} placeholder="매핑 결과의 원문 인용구" /></label>
        <label className="grid gap-2 text-sm font-medium">원문 위치<input className="h-10 rounded-md border bg-background px-3" value={location} onChange={(event) => setLocation(event.target.value)} placeholder="p.2 · 경력기술서" /></label>
        <label className="grid gap-2 text-sm font-medium">수정 사유<input className="h-10 rounded-md border bg-background px-3" value={editReason} onChange={(event) => setEditReason(event.target.value)} /></label>
        <label className="grid gap-2 text-sm font-medium">{role === "HR" ? "HR 스크리닝 판정" : "HM 서류 전형 판정"}<select className="h-10 rounded-md border bg-background px-3" value={verdict} onChange={(event) => setVerdict(event.target.value)}><option value="">판정 선택(선택 사항)</option>{verdictOptions.map((option) => <option key={option} value={option}>{option}</option>)}</select></label>
        <Button type="button" onClick={save}>내 판단 저장</Button>
      </CardContent></Card>
    </div>
    <Card><CardHeader><CardTitle>HR·HM 의견 비교</CardTitle><CardDescription>대표 결론을 자동 선택하지 않고 양쪽 근거를 함께 보존합니다.</CardDescription></CardHeader><CardContent className="grid gap-3">{selectedRow && <><p className="text-xs text-muted-foreground">차이: {selectedRow.differences.length ? selectedRow.differences.join(" · ") : "없음"}</p><div className="grid gap-3 md:grid-cols-2">{(["HR", "HM"] as ReviewerRole[]).map((reviewer) => { const review = reviewer === "HR" ? selectedRow.hr_review : selectedRow.hm_review; return <div className="rounded-md border p-4" key={reviewer}><p className="font-medium">{reviewer} · {review ? STATUS_LABELS[review.status] : "미입력"}</p><p className="mt-2 text-sm">{review?.reason_text ?? "아직 판단 로그가 없습니다."}</p>{review?.citation && <blockquote className="mt-2 border-l-2 pl-3 text-sm">“{review.citation}”</blockquote>}<p className="mt-2 text-xs text-muted-foreground">{review?.source_location ?? "근거 위치 없음"}</p>{review?.edit_history?.length ? <p className="mt-2 text-xs text-muted-foreground">수정 이력 {review.edit_history.length}건 · 감사 기록 보존됨</p> : null}</div>; })}</div></>}</CardContent></Card>
    <div className="flex justify-end">{canContinue ? <Link className="inline-flex h-10 items-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground" href={`/handoff?application_id=${encodeURIComponent(applicationId)}&criteria_version_id=${encodeURIComponent(versionId)}`}>다음: 핸드오프 카드 <span aria-hidden="true">→</span></Link> : <span className="text-xs text-muted-foreground">HR·HM의 모든 기준 판단을 저장하면 핸드오프 단계가 열립니다.</span>}</div>
  </section>;
}

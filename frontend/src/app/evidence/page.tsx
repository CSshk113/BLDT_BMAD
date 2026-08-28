"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EvidenceSplitView } from "@/components/criteria/EvidenceSplitView";
import { ApplicationApiError, getApplicationDocument, type ApplicationDocument } from "@/lib/applications-api";
import { getMappings, MappingApiError, type MappingResponse } from "@/lib/mapping-api";

export default function EvidencePage() {
  const [applicationId, setApplicationId] = useState("");
  const [criteriaVersionId, setCriteriaVersionId] = useState("cv-b2b-sales-v4");
  const [processingRunId, setProcessingRunId] = useState("");
  const [document, setDocument] = useState<ApplicationDocument | null>(null);
  const [result, setResult] = useState<MappingResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const searchParams = new URLSearchParams(window.location.search);
    setApplicationId(searchParams.get("application_id") ?? "");
    setCriteriaVersionId(searchParams.get("criteria_version_id") ?? "cv-b2b-sales-v4");
    setProcessingRunId(searchParams.get("run_id") ?? "");
  }, []);

  const openReview = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setError(""); setDocument(null); setResult(null); setLoading(true);
    if (!applicationId.trim() || !criteriaVersionId.trim()) {
      setError("지원서 ID와 기준 버전 ID를 입력하세요."); setLoading(false); return;
    }
    try {
      const mappings = await getMappings(applicationId.trim(), criteriaVersionId.trim(), processingRunId.trim() || undefined);
      const source = await getApplicationDocument(applicationId.trim(), mappings.processing_run_id);
      if (source.application_id !== mappings.application_id || source.criteria_version_id !== mappings.criteria_version_id || source.processing_run_id !== mappings.processing_run_id || source.artifact_id !== mappings.source_artifact_id) {
        throw new Error("매핑 결과와 원문 산출물의 실행 정보가 일치하지 않습니다");
      }
      setResult(mappings); setDocument(source);
    } catch (caught) {
      if (caught instanceof MappingApiError && caught.status === 404) setError("먼저 기준별 매핑을 실행해야 합니다.");
      else if (caught instanceof MappingApiError && caught.status === 409) setError("지원서 처리 완료와 정규화 Markdown 산출물을 먼저 확인하세요.");
      else if (caught instanceof ApplicationApiError && caught.status === 409) setError("지원서 처리 완료와 정규화 Markdown 산출물을 먼저 확인하세요.");
      else if (caught instanceof Error && caught.message.includes("실행 정보")) setError("매핑 결과와 원문 산출물이 다른 실행을 가리켜 검토를 중단했습니다.");
      else setError("원문 검토 화면을 불러오지 못했습니다. 지원서 ID와 서버 연결을 확인하세요.");
    } finally { setLoading(false); }
  };

  return <main className="mx-auto grid max-w-7xl gap-6 p-6" aria-labelledby="evidence-heading"><header><p className="text-xs font-semibold tracking-[0.18em] text-muted-foreground">EVIDENCE REVIEW · STORY 2.3</p><h1 id="evidence-heading" className="text-3xl font-semibold tracking-tight">원문과 근거를 한 화면에서 대조</h1><p className="mt-2 text-sm text-muted-foreground">PDF 좌표 대신 LlamaParse 정규화 Markdown의 실제 문자열을 검색합니다.</p></header><Card><CardHeader><CardTitle>검토 대상 열기</CardTitle><CardDescription>완료된 매핑 결과와 같은 처리 실행의 원문을 불러옵니다.</CardDescription></CardHeader><CardContent><form className="grid gap-4 md:grid-cols-[1fr_1fr_auto] md:items-end" onSubmit={openReview}><label className="grid gap-2 text-sm font-medium" htmlFor="evidence-application">지원서 ID<input id="evidence-application" className="h-10 rounded-md border bg-background px-3 text-sm font-normal" required placeholder="UPLOAD-..." value={applicationId} onChange={(event) => setApplicationId(event.target.value)} /></label><label className="grid gap-2 text-sm font-medium" htmlFor="evidence-criteria">기준 버전 ID<input id="evidence-criteria" className="h-10 rounded-md border bg-background px-3 text-sm font-normal" required value={criteriaVersionId} onChange={(event) => setCriteriaVersionId(event.target.value)} /></label><Button type="submit" disabled={loading || !applicationId.trim()}>{loading ? "불러오는 중…" : "검토 화면 열기"}</Button></form></CardContent></Card>{error && <Alert variant="destructive"><AlertTitle>검토 화면을 열 수 없습니다</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>}{result && document && <><EvidenceSplitView document={document} result={result} /><div className="flex justify-end"><Link className="inline-flex h-10 items-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground" href={`/judgments?application_id=${encodeURIComponent(result.application_id)}&criteria_version_id=${encodeURIComponent(result.criteria_version_id)}`}>다음: 판단 로그 <span aria-hidden="true">→</span></Link></div></>}</main>;
}

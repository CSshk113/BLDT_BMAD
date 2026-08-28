"use client";

import React, { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ProcessingList } from "@/components/applications/ProcessingList";
import { UploadForm } from "@/components/applications/UploadForm";
import { getApplication, listApplications, reprocessApplication, type ApplicationDetail, type ApplicationsList } from "@/lib/applications-api";

const emptyList: ApplicationsList = { items: [], total_ledger_count: 0, sample_count: 0, uploaded_count: 0 };

export default function ApplicationsPage() {
  const [catalog, setCatalog] = useState<ApplicationsList>(emptyList);
  const [selected, setSelected] = useState<ApplicationDetail | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [processingApplicationId, setProcessingApplicationId] = useState<string | null>(null);
  const selectedIdRef = useRef<string | null>(null);

  const selectDetail = (application: ApplicationDetail) => {
    selectedIdRef.current = application.id;
    setSelected(application);
  };

  const refresh = async (selectedId?: string) => {
    const result = await listApplications();
    setCatalog(result);
    const nextId = selectedId ?? selectedIdRef.current ?? result.items[0]?.id;
    if (!nextId) return;
    const application = await getApplication(nextId);
    if (selectedIdRef.current === null || selectedIdRef.current === nextId) selectDetail(application);
  };

  useEffect(() => {
    refresh().catch(() => setError("지원서 처리 목록을 불러오지 못했습니다. 백엔드 서버 연결을 확인하세요.")).finally(() => setLoading(false));
  }, []);

  const select = (id: string) => {
    selectedIdRef.current = id;
    getApplication(id).then((application) => {
      if (selectedIdRef.current === id) setSelected(application);
    }).catch(() => setError("지원서 상세 정보를 불러오지 못했습니다."));
  };
  const uploaded = (application: ApplicationDetail) => { selectDetail(application); refresh(application.id).catch(() => setError("업로드 후 목록을 갱신하지 못했습니다.")); };
  const retry = async () => {
    if (!selected || processingApplicationId) return;
    const applicationId = selected.id;
    setError("");
    setProcessingApplicationId(applicationId);
    try {
      const application = await reprocessApplication(applicationId);
      if (selectedIdRef.current === applicationId) setSelected(application);
      try {
        await refresh(applicationId);
      } catch {
        setError("처리는 시작됐지만 목록을 갱신하지 못했습니다.");
      }
    } catch {
      setError("처리를 시작하지 못했습니다.");
    } finally {
      setProcessingApplicationId(null);
    }
  };
  const hasCurrentOriginalPdf = selected?.artifacts.some((artifact) => artifact.artifact_type === "ORIGINAL_PDF" && artifact.is_current) ?? false;
  const canStartProcessing = selected?.source_type === "SAMPLE" && selected.processing_status === null && hasCurrentOriginalPdf;
  const canRetryProcessing = selected?.processing_status === "FAILED" && hasCurrentOriginalPdf;

  return <main className="mx-auto grid max-w-7xl gap-6 p-6" aria-labelledby="applications-heading">
    <header className="flex flex-wrap items-end justify-between gap-4"><div><p className="text-xs font-semibold tracking-[0.18em] text-muted-foreground">APPLICATION INTAKE · STORY 2.1</p><h1 id="applications-heading" className="text-3xl font-semibold tracking-tight">지원서 원문 처리</h1><p className="mt-2 text-sm text-muted-foreground">PDF를 받아 LlamaParse Markdown으로 변환하고, 실패한 처리도 숨기지 않습니다.</p></div><div className="flex gap-2"><Badge variant="outline">원장 {catalog.total_ledger_count}건</Badge><Badge variant="outline">PDF 표본 {catalog.sample_count}건</Badge><Badge variant="outline">직접 업로드 {catalog.uploaded_count}건</Badge></div></header>
    {error && <Alert variant="destructive"><AlertTitle>오류</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>}
    <div className="grid gap-6 lg:grid-cols-[0.8fr_1.2fr]"><UploadForm onUploaded={uploaded} /><div>{loading ? <Card><CardContent className="p-6 text-sm text-muted-foreground">처리 목록을 불러오는 중…</CardContent></Card> : <ProcessingList items={catalog.items} selectedId={selected?.id ?? ""} onSelect={select} />}</div></div>
    <Card aria-label="선택한 지원서 상세"><CardHeader><CardTitle>처리 상세</CardTitle><CardDescription>원본 파일과 LlamaParse 산출물은 같은 지원서·실행 ID로 연결됩니다.</CardDescription></CardHeader><CardContent>{selected ? <div className="grid gap-4"><div className="flex flex-wrap items-center justify-between gap-3"><div><p className="font-medium">{selected.candidate_token} · {selected.position_name}</p><p className="text-xs text-muted-foreground">{selected.id} · 기준 {selected.criteria_version_id ?? "없음"}</p></div><div className="flex gap-2">{selected.can_review && <><Link className="inline-flex h-10 items-center rounded-md border px-4 text-sm font-medium" href={`/judgments?application_id=${encodeURIComponent(selected.id)}&criteria_version_id=${encodeURIComponent(selected.criteria_version_id ?? "")}`}>판단 로그</Link><Link className="inline-flex h-10 items-center rounded-md border px-4 text-sm font-medium" href={`/handoff?application_id=${encodeURIComponent(selected.id)}&criteria_version_id=${encodeURIComponent(selected.criteria_version_id ?? "")}`}>핸드오프 카드</Link><Link className="inline-flex h-10 items-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground" href={`/evidence?application_id=${encodeURIComponent(selected.id)}&criteria_version_id=${encodeURIComponent(selected.criteria_version_id ?? "")}&run_id=${encodeURIComponent(selected.last_successful_run_id ?? "")}`}>원문 근거 검토</Link></>}{canStartProcessing && <Button variant="outline" onClick={retry} disabled={processingApplicationId === selected.id}>{processingApplicationId === selected.id ? "처리 중…" : "처리 시작"}</Button>}{canRetryProcessing && <Button variant="outline" onClick={retry} disabled={processingApplicationId === selected.id}>{processingApplicationId === selected.id ? "처리 중…" : "다시 처리"}</Button>}</div></div><div className="grid gap-2 md:grid-cols-5">{["RECEIVED", "PARSING", "MAPPING", "COMPLETED"].map((step) => <div key={step} className={`rounded-md border p-3 text-xs ${selected.processing_status === step ? "border-primary bg-primary/5" : ""}`}><strong>{step}</strong><span className="mt-1 block text-muted-foreground">{selected.processing_status === step ? "현재 상태" : selected.processing_status === "FAILED" && selected.failed_step === step ? "실패 단계" : "대기"}</span></div>)}</div>{selected.failure_reason && <Alert variant="destructive"><AlertTitle>처리 실패 · {selected.failed_step}</AlertTitle><AlertDescription>{selected.failure_reason}</AlertDescription></Alert>}<div className="grid gap-2"><p className="text-sm font-medium">보존된 산출물</p>{selected.artifacts.length ? selected.artifacts.map((artifact) => <div key={artifact.id} className="flex justify-between rounded-md border p-3 text-sm"><span>{artifact.artifact_type}</span><span className="text-muted-foreground">{artifact.original_filename}{artifact.is_current ? " · 현재" : " · 이전"}</span></div>) : <p className="text-sm text-muted-foreground">아직 산출물이 없습니다.</p>}</div></div> : <p className="text-sm text-muted-foreground">왼쪽 목록에서 지원서를 선택하세요.</p>}</CardContent></Card>
  </main>;
}

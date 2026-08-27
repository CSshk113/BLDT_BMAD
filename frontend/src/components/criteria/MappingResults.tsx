"use client";

import React from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { MappingResponse } from "@/lib/mapping-api";

const evidenceVariant = (status: string) => status === "확인 불가" ? "outline" : status === "미충족" ? "destructive" : status === "부분 충족" ? "secondary" : "default";

export function EvidenceCard({
  mapping,
  interactive = false,
  active = false,
  onSelect,
}: {
  mapping: MappingResponse["mappings"][number];
  interactive?: boolean;
  active?: boolean;
  onSelect?: () => void;
}) {
  const activate = () => onSelect?.();
  return <article
    className={`grid gap-2 rounded-lg border p-4 ${active ? "border-primary bg-primary/5" : ""} ${interactive ? "cursor-pointer" : ""}`}
    role={interactive ? "button" : undefined}
    tabIndex={interactive ? 0 : undefined}
    aria-pressed={interactive ? active : undefined}
    aria-label={interactive ? `${mapping.criterion_text} 원문 인용구 선택` : undefined}
    onClick={interactive ? activate : undefined}
    onKeyDown={interactive ? (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); activate(); } } : undefined}
  >
    <div className="flex flex-wrap items-center justify-between gap-2"><div><p className="font-medium">{mapping.criterion_text}</p><p className="text-xs text-muted-foreground">{mapping.requirement_type} · {mapping.criterion_item_id}</p></div><Badge variant={evidenceVariant(mapping.evidence_status) as "default" | "secondary" | "destructive" | "outline"}>{mapping.evidence_status}</Badge></div>
    {mapping.citation ? <blockquote className="border-l-2 pl-3 text-sm leading-6">“{mapping.citation}”</blockquote> : <p className="text-sm text-muted-foreground">원문에서 확인 가능한 근거가 없습니다.</p>}
    <p className="text-xs text-muted-foreground">{mapping.location_kind === "FALLBACK" ? "문맥 보기 fallback · " : ""}{mapping.location}</p>
  </article>;
}

export function MappingResults({ result }: { result: MappingResponse }) {
  return <section className="grid gap-4" aria-label="기준별 원문 매핑 결과">
    {result.is_preview && <Alert><AlertTitle>Draft 미리보기</AlertTitle><AlertDescription>아직 승인되지 않은 기준의 탐색 결과입니다. 공식 판단이나 핸드오프로 사용되지 않습니다.</AlertDescription></Alert>}
    <Card><CardHeader><CardTitle>기준별 원문 인용구</CardTitle><CardDescription>{result.application_id} · 기준 {result.criteria_version_id} · 실행 {result.processing_run_id} · 원문 산출물 {result.source_artifact_id}</CardDescription></CardHeader><CardContent className="grid gap-3">
      {result.mappings.map((mapping) => <EvidenceCard key={mapping.id} mapping={mapping} />)}
    </CardContent></Card>
  </section>;
}

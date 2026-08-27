"use client";

import React, { useRef, useState } from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { ApplicationDocument } from "@/lib/applications-api";
import type { MappingResponse } from "@/lib/mapping-api";
import { EvidenceCard } from "./MappingResults";

function highlightedContent(content: string, citation: string, markRef: React.RefObject<HTMLElement>) {
  if (!citation) return content;
  const start = content.indexOf(citation);
  if (start < 0) return content;
  return <>{content.slice(0, start)}<mark ref={markRef} className="rounded bg-yellow-200 px-0.5 text-foreground" data-active-citation="true">{citation}</mark>{content.slice(start + citation.length)}</>;
}

function nativeFind(citation: string) {
  const find = (window as Window & { find?: (text: string, caseSensitive?: boolean, backwards?: boolean, wrapAround?: boolean, wholeWord?: boolean, searchInFrames?: boolean, showDialog?: boolean) => boolean }).find;
  if (find) find(citation, false, false, true, false, false, false);
}

export function EvidenceSplitView({ document, result }: { document: ApplicationDocument; result: MappingResponse }) {
  const [activeId, setActiveId] = useState<string | null>(null);
  const [announcement, setAnnouncement] = useState("근거 카드를 선택하면 왼쪽 원문에서 확인합니다.");
  const [matchFailed, setMatchFailed] = useState(false);
  const markRef = useRef<HTMLElement>(null);

  const selectMapping = (mapping: MappingResponse["mappings"][number]) => {
    setActiveId(mapping.id);
    const matched = Boolean(mapping.citation) && document.content.includes(mapping.citation);
    setMatchFailed(!matched);
    if (matched) {
      nativeFind(mapping.citation);
      setAnnouncement("원문에서 인용구를 찾았습니다. 왼쪽에 하이라이트했습니다.");
      window.setTimeout(() => markRef.current?.scrollIntoView({ block: "center" }), 0);
    } else {
      window.getSelection()?.removeAllRanges();
      setAnnouncement("원문 일치 실패입니다. 오른쪽 카드의 문맥 보기 fallback을 확인하세요.");
    }
  };

  const activeMapping = result.mappings.find((mapping) => mapping.id === activeId);
  return <section className="grid gap-4" aria-label="지원서 근거 대조 화면">
    <div className="flex flex-wrap items-center gap-2 rounded-lg border bg-card px-4 py-3 text-sm"><span className="font-medium">지원서 {result.application_id}</span><span className="text-muted-foreground">· 기준 {result.criteria_version_id}</span><Badge variant={result.is_preview ? "secondary" : "default"}>{result.is_preview ? "Draft 미리보기" : "승인 기준"}</Badge><span className="ml-auto text-xs text-muted-foreground">실행 {document.processing_run_id}</span></div>
    <p aria-live="polite" className="rounded-md bg-muted px-3 py-2 text-sm">{announcement}</p>
    {matchFailed && activeMapping && <Alert variant="destructive"><AlertTitle>원문 일치 실패</AlertTitle><AlertDescription>저장된 인용구가 현재 Markdown 원문에 없어 하이라이트하지 않았습니다. {activeMapping.location_kind === "FALLBACK" ? "오른쪽의 문맥 보기 fallback을 확인하세요." : "저장된 위치와 문맥을 확인하세요."}</AlertDescription></Alert>}
    <div className="grid min-h-0 gap-4 lg:grid-cols-[1.1fr_0.9fr]">
      <Card className="min-h-0"><CardHeader><CardTitle>지원서 원문</CardTitle><CardDescription>정규화 Markdown · 산출물 {document.artifact_id}</CardDescription></CardHeader><CardContent className="max-h-[calc(100vh-17rem)] min-h-[28rem] overflow-y-auto"><pre className="whitespace-pre-wrap break-words font-sans text-sm leading-7">{activeMapping ? highlightedContent(document.content, activeMapping.citation, markRef) : document.content}</pre></CardContent></Card>
      <Card className="min-h-0"><CardHeader><CardTitle>기준별 근거</CardTitle><CardDescription>카드를 선택하면 왼쪽 원문을 검색합니다.</CardDescription></CardHeader><CardContent className="max-h-[calc(100vh-17rem)] min-h-[28rem] space-y-3 overflow-y-auto">{result.mappings.length ? result.mappings.map((mapping) => <EvidenceCard key={mapping.id} mapping={mapping} interactive active={mapping.id === activeId} onSelect={() => selectMapping(mapping)} />) : <p className="rounded-md border border-dashed p-4 text-sm text-muted-foreground">검토 가능한 근거가 없습니다.</p>}</CardContent></Card>
    </div>
  </section>;
}

"use client";

import React from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { ApplicationSummary, ProcessingStatus } from "@/lib/applications-api";

const statusLabel: Record<ProcessingStatus, string> = { RECEIVED: "접수됨", PARSING: "파싱 중", MAPPING: "변환·정규화 중", COMPLETED: "처리 완료", FAILED: "처리 실패" };

type ProcessingListProps = { items: ApplicationSummary[]; selectedId: string; onSelect: (id: string) => void };

export function ProcessingList({ items, selectedId, onSelect }: ProcessingListProps) {
  return (
    <Card className="min-h-0">
      <CardHeader><CardTitle>지원서 처리 목록</CardTitle><CardDescription>원장 후보와 PDF 표본을 분리해 현재 처리 상태를 표시합니다.</CardDescription></CardHeader>
      <CardContent className="h-[80vh] min-h-0 flex-none overflow-y-auto">
        <div className="grid gap-2">
          {items.length === 0 && <p className="text-sm text-muted-foreground">아직 지원서가 없습니다.</p>}
          {items.map((item) => {
            const isLedgerOnly = item.source_type === "LEDGER_ONLY";
            return <Button key={item.id} type="button" variant={selectedId === item.id ? "secondary" : "outline"} aria-pressed={selectedId === item.id} className="h-auto justify-between gap-3 py-3 text-left" onClick={() => onSelect(item.id)}>
              <span className="grid min-w-0 gap-1"><span className="truncate font-medium">{item.candidate_token} · {item.position_name}</span><span className="truncate text-xs text-muted-foreground">{item.ledger_metadata.channel ?? "채널 미상"} · {item.ledger_metadata.applied_at ?? "지원일 미상"} · {item.id}</span></span>
              <span className="flex shrink-0 items-center gap-2">{isLedgerOnly ? <Badge variant="outline">원장 데이터만 있음</Badge> : <Badge variant={item.processing_status === "FAILED" ? "destructive" : item.processing_status === "COMPLETED" ? "default" : "secondary"}>{item.processing_status ? statusLabel[item.processing_status] : item.list_status}</Badge>}</span>
            </Button>;
          })}
        </div>
      </CardContent>
    </Card>
  );
}

"use client";

import React, { useState } from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { MappingResults } from "@/components/criteria/MappingResults";
import { createMappings, MappingApiError, type MappingResponse } from "@/lib/mapping-api";

export default function MappingPage() {
  const [applicationId, setApplicationId] = useState("");
  const [criteriaVersionId, setCriteriaVersionId] = useState("cv-b2b-sales-v4");
  const [result, setResult] = useState<MappingResponse | null>(null);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    setSaving(true);
    try {
      setResult(await createMappings(applicationId.trim(), criteriaVersionId.trim()));
    } catch (caught) {
      if (caught instanceof MappingApiError && caught.status === 409) {
        setError("지원서의 PDF 처리 완료와 정규화 Markdown 산출물을 먼저 확인하세요.");
      } else if (caught instanceof MappingApiError && caught.status === 404) {
        setError("해당 지원서의 기준별 매핑 결과를 찾지 못했습니다.");
      } else {
        setError("매핑 서버에 연결하지 못했습니다. 잠시 후 다시 시도하세요.");
      }
    } finally {
      setSaving(false);
    }
  };

  return <main className="mx-auto grid max-w-5xl gap-6 p-6" aria-labelledby="mapping-heading">
    <header><p className="text-xs font-semibold tracking-[0.18em] text-muted-foreground">EVIDENCE MAPPING · STORY 2.2</p><h1 id="mapping-heading" className="text-3xl font-semibold tracking-tight">기준별 원문 인용구 매핑</h1><p className="mt-2 text-sm text-muted-foreground">AI 요약 대신 정규화 Markdown에서 실제로 확인되는 원문만 표시합니다.</p></header>
    <Card><CardHeader><CardTitle>매핑 실행</CardTitle><CardDescription>처리 완료된 지원서와 기준 버전 ID를 입력하세요.</CardDescription></CardHeader><CardContent><form className="grid gap-4 md:grid-cols-[1fr_1fr_auto] md:items-end" onSubmit={submit}>
      <div className="grid gap-2"><Label htmlFor="mapping-application">지원서 ID</Label><Input id="mapping-application" required placeholder="UPLOAD-..." value={applicationId} onChange={(event) => setApplicationId(event.target.value)} /></div>
      <div className="grid gap-2"><Label htmlFor="mapping-criteria">기준 버전 ID</Label><Input id="mapping-criteria" required value={criteriaVersionId} onChange={(event) => setCriteriaVersionId(event.target.value)} /></div>
      <Button type="submit" disabled={saving || !applicationId.trim()}>{saving ? "매핑 중…" : "기준별 매핑 실행"}</Button>
    </form></CardContent></Card>
    {error && <Alert variant="destructive"><AlertTitle>매핑할 수 없습니다</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>}
    {result && <MappingResults result={result} />}
  </main>;
}

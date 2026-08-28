"use client";

import { useState } from "react";
import React from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApplicationApiError, uploadApplication, type ApplicationDetail } from "@/lib/applications-api";

type UploadFormProps = { onUploaded: (application: ApplicationDetail) => void };

export function UploadForm({ onUploaded }: UploadFormProps) {
  const [file, setFile] = useState<File | null>(null);
  const [candidateToken, setCandidateToken] = useState("후보-업로드-001");
  const [positionName, setPositionName] = useState("B2B 영업 매니저 5년 이상");
  const [criteriaVersionId, setCriteriaVersionId] = useState("cv-b2b-sales-v4");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!file) return setError("업로드할 PDF를 선택하세요.");
    if (!file.name.toLowerCase().endsWith(".pdf")) return setError("PDF 파일만 업로드할 수 있습니다.");
    setError("");
    setSaving(true);
    try {
      onUploaded(await uploadApplication({ file, candidateToken, positionName, criteriaVersionId }));
      setFile(null);
      event.currentTarget.reset();
    } catch (caught) {
      if (caught instanceof ApplicationApiError && caught.status === 415) {
        setError("PDF 파일만 업로드할 수 있습니다.");
      } else if (caught instanceof ApplicationApiError && caught.status === 413) {
        setError("PDF 파일은 10MB 이하만 업로드할 수 있습니다.");
      } else if (caught instanceof ApplicationApiError) {
        setError("PDF 업로드 요청에 실패했습니다. 서버 연결과 입력값을 확인하세요.");
      } else {
        setError("PDF 업로드 서버에 연결하지 못했습니다. 백엔드 상태를 확인하세요.");
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>PDF 지원서 업로드</CardTitle>
        <CardDescription>서버에서 PDF를 LlamaParse Markdown으로 변환합니다. API 키는 브라우저에 노출되지 않습니다.</CardDescription>
      </CardHeader>
      <CardContent>
        <form className="grid gap-4" onSubmit={submit}>
          {error && <Alert variant="destructive"><AlertTitle>업로드할 수 없습니다</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>}
          <div className="grid gap-2"><Label htmlFor="application-file">지원서 PDF</Label><Input id="application-file" type="file" accept="application/pdf,.pdf" onChange={(event) => setFile(event.target.files?.[0] ?? null)} /></div>
          <div className="grid gap-2"><Label htmlFor="candidate-token">후보 식별자</Label><Input id="candidate-token" value={candidateToken} onChange={(event) => setCandidateToken(event.target.value)} /></div>
          <div className="grid gap-2"><Label htmlFor="position-name">포지션</Label><Input id="position-name" value={positionName} onChange={(event) => setPositionName(event.target.value)} /></div>
          <div className="grid gap-2"><Label htmlFor="criteria-version-id">기준 버전 ID</Label><Input id="criteria-version-id" value={criteriaVersionId} onChange={(event) => setCriteriaVersionId(event.target.value)} /></div>
          <div className="flex items-center justify-between gap-3"><span className="text-xs text-muted-foreground">PDF → RECEIVED → PARSING → MAPPING → COMPLETED</span><Button type="submit" disabled={saving}>{saving ? "처리 중…" : "PDF 접수 및 처리"}</Button></div>
        </form>
      </CardContent>
    </Card>
  );
}

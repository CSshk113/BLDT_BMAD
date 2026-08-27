"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { JudgmentWorkspace } from "@/components/judgments/JudgmentWorkspace";

export default function JudgmentsPage() {
  const [applicationId, setApplicationId] = useState("APPS-2");
  const [versionId, setVersionId] = useState("cv-b2b-sales-v4");
  const [opened, setOpened] = useState(false);
  useEffect(() => { const params = new URLSearchParams(window.location.search); setApplicationId(params.get("application_id") ?? "APPS-2"); setVersionId(params.get("criteria_version_id") ?? "cv-b2b-sales-v4"); }, []);
  return <main className="mx-auto grid max-w-7xl gap-6 p-6"><header><p className="text-xs font-semibold tracking-[0.18em] text-muted-foreground">DECISION LOG · STORY 3.1</p><h1 className="text-3xl font-semibold tracking-tight">판단 로그와 HR·HM 의견 비교</h1><p className="mt-2 text-sm text-muted-foreground">승인된 기준과 완료된 근거 매핑 위에서 사람의 판단 맥락을 보존합니다.</p></header><div className="grid gap-4 md:grid-cols-[1fr_1fr_auto] md:items-end"><label className="grid gap-2 text-sm font-medium">지원서 ID<input className="h-10 rounded-md border bg-background px-3" value={applicationId} onChange={(event) => setApplicationId(event.target.value)} /></label><label className="grid gap-2 text-sm font-medium">기준 버전 ID<input className="h-10 rounded-md border bg-background px-3" value={versionId} onChange={(event) => setVersionId(event.target.value)} /></label><Button type="button" onClick={() => setOpened(true)}>공식 판단 열기</Button></div>{opened && <JudgmentWorkspace applicationId={applicationId} versionId={versionId} />}</main>;
}

"use client";

import { useEffect, useState } from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { generateHandoffCard, type HandoffCard } from "@/lib/handoff-api";

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
  const [error, setError] = useState("");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setApplicationId(params.get("application_id") ?? "APPS-2");
    setVersionId(params.get("criteria_version_id") ?? "cv-b2b-sales-v4");
  }, []);

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
      setCard((await generateHandoffCard(nextVersionId, nextApplicationId)).card);
    } catch {
      setCard(null);
      setError("핸드오프 생성 조건을 확인하세요. 승인 기준·완료 매핑·원문·HR/HM 판단 로그가 모두 필요합니다.");
    }
  };

  const judgmentRows = card
    ? (((card.payload.judgments as { rows?: JudgmentRow[] }).rows ?? []))
    : [];

  return (
    <main className="mx-auto grid max-w-7xl gap-6 p-6">
      <header>
        <p className="text-xs font-semibold tracking-[0.18em] text-muted-foreground">HANDOFF CARD · STORY 3.2</p>
        <h1 className="text-3xl font-semibold tracking-tight">현업 핸드오프 카드</h1>
        <p className="mt-2 text-sm text-muted-foreground">양쪽 판단과 원문 근거를 한 장의 JSON 카드로 고정합니다.</p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>카드 생성</CardTitle>
          <CardDescription>승인된 기준과 처리 완료된 지원서만 공식 카드로 만들 수 있습니다.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-[1fr_1fr_auto] md:items-end">
          <label className="grid gap-2 text-sm font-medium">
            지원서 ID
            <input className="h-10 rounded-md border bg-background px-3" value={applicationId} onChange={(event) => setApplicationId(event.target.value)} />
          </label>
          <label className="grid gap-2 text-sm font-medium">
            기준 버전 ID
            <input className="h-10 rounded-md border bg-background px-3" value={versionId} onChange={(event) => setVersionId(event.target.value)} />
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

          <p className="text-xs text-muted-foreground">질문 후보와 면접 결과는 다음 스토리에서 이 카드의 JSON payload에 확장됩니다.</p>
        </section>
      )}
    </main>
  );
}

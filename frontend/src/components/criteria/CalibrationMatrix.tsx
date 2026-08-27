"use client";

import React, { useEffect, useState } from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import type { ReviewInput, ReviewLog, ReviewMatrix, ReviewRow, ReviewStatus, ReviewerRole } from "@/lib/criteria-api";

type CalibrationMatrixProps = {
  matrix: ReviewMatrix;
  currentRole: ReviewerRole;
  onRoleChange: (role: ReviewerRole) => void;
  onSave: (review: ReviewInput) => Promise<void>;
  onResolve?: (itemId: string, reason: string) => Promise<void>;
};

const STATUS_LABELS: Record<ReviewStatus, string> = {
  FULFILLED: "충족",
  PARTIALLY_FULFILLED: "부분 충족",
  UNFULFILLED: "미충족",
  UNVERIFIABLE: "확인 불가",
};

const ROLE_LABELS: Record<ReviewerRole, string> = {
  HR: "HR · 스크리닝",
  HM: "HM · 서류 심사",
};

function statusVariant(status: ReviewStatus) {
  if (status === "FULFILLED") return "default" as const;
  if (status === "UNFULFILLED") return "destructive" as const;
  return "outline" as const;
}

function ReviewCell({ review, role }: { review: ReviewLog | null; role: ReviewerRole }) {
  if (!review) {
    return <span className="text-xs text-muted-foreground">아직 검토하지 않음 · {ROLE_LABELS[role]}</span>;
  }
  return (
    <div className="grid gap-1.5">
      <Badge variant={statusVariant(review.status)}>{STATUS_LABELS[review.status]}</Badge>
      <span className="max-w-56 whitespace-normal text-xs leading-5 text-foreground">{review.reason_text}</span>
      <span className="text-xs text-muted-foreground">근거 위치 · {review.source_location}</span>
    </div>
  );
}

function ConflictBadge({ row }: { row: ReviewRow }) {
  if (row.conflict_status === "OPEN") return <Badge variant="destructive">충돌 {row.differences.length}건</Badge>;
  if (row.conflict_status === "RESOLVED") return <Badge variant="secondary">해결됨</Badge>;
  if (row.conflict_status === "PENDING") return <Badge variant="outline">검토 대기</Badge>;
  return <Badge variant="secondary">일치</Badge>;
}

export function CalibrationMatrix({ matrix, currentRole, onRoleChange, onSave, onResolve }: CalibrationMatrixProps) {
  const [selectedItemId, setSelectedItemId] = useState(matrix.rows[0]?.criterion_item_id ?? "");
  const [status, setStatus] = useState<ReviewStatus>("UNVERIFIABLE");
  const [reason, setReason] = useState("");
  const [location, setLocation] = useState("");
  const [resolutionReason, setResolutionReason] = useState("");
  const [saving, setSaving] = useState(false);
  const selectedRow = matrix.rows.find((row) => row.criterion_item_id === selectedItemId) ?? matrix.rows[0];

  useEffect(() => {
    const row = matrix.rows.find((candidate) => candidate.criterion_item_id === selectedItemId) ?? matrix.rows[0];
    if (!row) return;
    const existing = currentRole === "HR" ? row.hr_review : row.hm_review;
    if (row.criterion_item_id !== selectedItemId) setSelectedItemId(row.criterion_item_id);
    setStatus(existing?.status ?? "UNVERIFIABLE");
    setReason(existing?.reason_text ?? "");
    setLocation(existing?.source_location ?? "");
    setResolutionReason(row.resolution?.resolution_reason ?? "");
  }, [currentRole, matrix, selectedItemId]);

  const selectRow = (row: ReviewRow) => {
    const existing = currentRole === "HR" ? row.hr_review : row.hm_review;
    setSelectedItemId(row.criterion_item_id);
    setStatus(existing?.status ?? "UNVERIFIABLE");
    setReason(existing?.reason_text ?? "");
    setLocation(existing?.source_location ?? "");
  };

  const submit = async () => {
    if (!selectedRow || !reason.trim() || !location.trim()) return;
    setSaving(true);
    try {
      await onSave({ criterion_item_id: selectedRow.criterion_item_id, status, reason_text: reason.trim(), source_location: location.trim() });
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="grid gap-4" aria-labelledby="calibration-matrix-heading">
      <Card>
        <CardHeader className="border-b">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <CardTitle id="calibration-matrix-heading">교정 표본 · {matrix.application_id}</CardTitle>
              <CardDescription>같은 지원서를 독립적으로 검토하고, 상태·근거 위치·사유 차이를 비교합니다.</CardDescription>
            </div>
            <div className="grid gap-2">
              <Label>현재 검토자</Label>
              <RadioGroup value={currentRole} onValueChange={(value) => onRoleChange(value as ReviewerRole)} className="flex gap-2">
                {(Object.keys(ROLE_LABELS) as ReviewerRole[]).map((role) => (
                  <Label key={role} className="flex cursor-pointer items-center gap-2 rounded-md border px-3 py-2 text-xs">
                    <RadioGroupItem value={role} aria-label={ROLE_LABELS[role]} />
                    {ROLE_LABELS[role]}
                  </Label>
                ))}
              </RadioGroup>
              <span className="text-xs text-muted-foreground">다른 검토자의 기록은 읽기 전용으로 표시됩니다.</span>
            </div>
          </div>
        </CardHeader>
        <CardContent className="grid gap-4 pt-4">
          <Alert variant={matrix.open_conflict_count > 0 ? "destructive" : "default"}>
            <AlertTitle>{matrix.open_conflict_count > 0 ? `열린 충돌 ${matrix.open_conflict_count}건` : "열린 충돌 없음"}</AlertTitle>
            <AlertDescription>충돌은 시스템이 합치지 않습니다. 담당자가 원문 근거를 확인한 뒤 별도로 해결해야 합니다.</AlertDescription>
          </Alert>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-56">평가 기준</TableHead>
                <TableHead>HR · 스크리닝</TableHead>
                <TableHead>HM · 서류 심사</TableHead>
                <TableHead>비교</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {matrix.rows.map((row) => (
                <TableRow key={row.criterion_item_id} data-state={row.criterion_item_id === selectedItemId ? "selected" : undefined}>
                  <TableCell className="whitespace-normal align-top">
                    <button type="button" className="text-left" onClick={() => selectRow(row)}>
                      <span className="mb-1 block text-xs text-muted-foreground">{row.requirement_type}</span>
                      <span className="font-medium">{row.criterion_text}</span>
                    </button>
                  </TableCell>
                  <TableCell className="align-top"><ReviewCell review={row.hr_review} role="HR" /></TableCell>
                  <TableCell className="align-top"><ReviewCell review={row.hm_review} role="HM" /></TableCell>
                  <TableCell className="align-top">
                    <div className="grid gap-1">
                      <ConflictBadge row={row} />
                      {row.differences.length > 0 && <span className="text-xs text-destructive">차이: {row.differences.join(" · ")}</span>}
                      {row.resolution && <span className="text-xs text-muted-foreground">해결 사유: {row.resolution.resolution_reason}</span>}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {selectedRow && (
        <div className="grid gap-4">
        <Card>
          <CardHeader>
            <CardTitle>{ROLE_LABELS[currentRole]} 검토 입력</CardTitle>
            <CardDescription>{selectedRow.criterion_text} · {currentRole}의 독립 판단을 저장합니다.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4">
            <div className="grid gap-2">
              <Label>기준 상태</Label>
              <RadioGroup value={status} onValueChange={(value) => setStatus(value as ReviewStatus)} className="grid grid-cols-2 gap-2 md:grid-cols-4">
                {(Object.keys(STATUS_LABELS) as ReviewStatus[]).map((value) => (
                  <Label key={value} className="flex cursor-pointer items-center gap-2 rounded-md border px-3 py-2 text-xs">
                    <RadioGroupItem value={value} aria-label={STATUS_LABELS[value]} />
                    {STATUS_LABELS[value]}
                  </Label>
                ))}
              </RadioGroup>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="review-source-location">원문 위치</Label>
              <Input id="review-source-location" value={location} onChange={(event) => setLocation(event.target.value)} placeholder="예: p.2 · 경력기술서" />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="review-reason">판단 사유</Label>
              <Textarea id="review-reason" value={reason} onChange={(event) => setReason(event.target.value)} placeholder="원문에서 확인한 근거와 판단 이유를 남겨주세요." />
            </div>
            <div className="flex items-center justify-between gap-3">
              <span className="text-xs text-muted-foreground">저장 후에도 HR/HM 의견은 자동으로 합쳐지지 않습니다.</span>
              <Button type="button" onClick={submit} disabled={saving || !reason.trim() || !location.trim()}>{saving ? "저장 중…" : "독립 검토 저장"}</Button>
            </div>
          </CardContent>
        </Card>
        {selectedRow.conflict_status === "OPEN" && currentRole === "HR" && onResolve && (
          <Card>
            <CardHeader>
              <CardTitle>충돌 해결</CardTitle>
              <CardDescription>양쪽 판단은 보존한 채, HR의 해결 사유만 추가합니다.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-3">
              <Label htmlFor="conflict-resolution-reason">해결 사유</Label>
              <Textarea id="conflict-resolution-reason" value={resolutionReason} onChange={(event) => setResolutionReason(event.target.value)} placeholder="충돌을 어떻게 확인하고 해결했는지 남겨주세요." />
              <div className="flex justify-end">
                <Button type="button" variant="secondary" onClick={() => onResolve(selectedRow.criterion_item_id, resolutionReason.trim())} disabled={!resolutionReason.trim()}>충돌 해결 기록</Button>
              </div>
            </CardContent>
          </Card>
        )}
        </div>
      )}
    </section>
  );
}

"use client";

import { useEffect, useState } from "react";
import React from "react";
import { CriteriaItem, CriteriaVersionPanel } from "@/components/criteria/CriteriaVersionPanel";
import { GateBanner } from "@/components/criteria/GateBanner";
import { CalibrationMatrix } from "@/components/criteria/CalibrationMatrix";
import {
  createDraft,
  fallbackReviewMatrix,
  loadCriteria,
  loadPreview,
  loadReviewMatrix,
  isNetworkError,
  approveCriteria,
  generateHandoff,
  resolveConflict,
  saveDraft,
  saveReview,
  normalizeSourceLocation,
  toUiItems,
  type ReviewInput,
  type ReviewLog,
  type ReviewMatrix,
  type ConflictResolution,
  type CriteriaVersionStatus,
  type ReviewerRole,
} from "@/lib/criteria-api";

const initialItems: CriteriaItem[] = [
  { id: "item-1", text: "콜드 아웃바운드 영업 경험", type: "필수" },
  { id: "item-2", text: "B2B 세일즈 파이프라인 운영 경험", type: "필수" },
  { id: "item-3", text: "CRM 또는 세일즈 데이터 기반 성과 관리", type: "우대" },
];

export default function CalibrationPage() {
  const [versionId, setVersionId] = useState("cv-b2b-sales-v4");
  const [versionStatus, setVersionStatus] = useState<CriteriaVersionStatus>("DRAFT");
  const [items, setItems] = useState(initialItems);
  const [editing, setEditing] = useState(false);
  const [invalidated, setInvalidated] = useState(false);
  const [savedMessage, setSavedMessage] = useState("");
  const [previewStatus, setPreviewStatus] = useState<"COMPLETED" | "INVALIDATED">("COMPLETED");
  const [currentRole, setCurrentRole] = useState<ReviewerRole>("HR");
  const [reviewMatrix, setReviewMatrix] = useState<ReviewMatrix>(() => fallbackReviewMatrix("cv-b2b-sales-v4", initialItems));
  const [reviewLoading, setReviewLoading] = useState(true);
  const [reviewError, setReviewError] = useState("");
  const [reviewLoadError, setReviewLoadError] = useState("");

  useEffect(() => {
    let active = true;
    setReviewLoading(true);
    setReviewError("");
    setReviewLoadError("");
    Promise.all([loadCriteria(versionId), loadPreview(versionId)])
      .then(async ([criteriaResult, preview]) => {
        if (!active) return;
        setItems(criteriaResult.items);
        setVersionStatus(criteriaResult.version.status);
        const matrix = await loadReviewMatrix(versionId, criteriaResult.items);
        if (!active) return;
        setReviewMatrix(matrix);
        const mappingStatus = preview.mappings[0]?.mapping_status;
        if (mappingStatus === "INVALIDATED") {
          setPreviewStatus("INVALIDATED");
          setInvalidated(true);
        }
      })
      .catch((error) => {
        // The static demo state remains usable when the API is not running yet.
        if (!active) return;
        if (isNetworkError(error)) setReviewMatrix(fallbackReviewMatrix(versionId, items));
        else setReviewLoadError("교정 표본을 불러오지 못했습니다. 서버 응답을 확인하세요.");
      })
      .finally(() => {
        if (active) setReviewLoading(false);
      });
    return () => {
      active = false;
    };
  }, [versionId]); // eslint-disable-line react-hooks/exhaustive-deps

  const updateItem = (id: string, value: string) => {
    setItems((current) => current.map((item) => (item.id === id ? { ...item, text: value } : item)));
  };

  const saveChanges = async () => {
    setEditing(false);
    try {
      const result = await saveDraft(versionId, items);
      setItems(toUiItems(result.version));
      setVersionStatus(result.version.status);
      setInvalidated(result.rerun_required);
      setPreviewStatus(result.rerun_required ? "INVALIDATED" : "COMPLETED");
      setSavedMessage(`저장 완료 · 기존 매핑 ${result.invalidated_mapping_count}건을 ${result.rerun_required ? "무효화했습니다" : "유지했습니다"}.`);
    } catch {
      setInvalidated(true);
      setPreviewStatus("INVALIDATED");
      setSavedMessage("로컬 데모 저장 완료 · 기존 매핑 1건을 무효화했습니다. 재실행이 필요합니다.");
    }
  };

  const createVersion = async () => {
    try {
      const created = await createDraft(versionId);
      setVersionId(created.id);
      setItems(toUiItems(created));
      setVersionStatus(created.status);
    } catch {
      setVersionId(`cv-b2b-sales-v4-draft-${Date.now().toString().slice(-4)}`);
    }
    setInvalidated(false);
    setPreviewStatus("COMPLETED");
    setSavedMessage("새 Draft 기준 버전을 만들었습니다. HM 승인 전까지 탐색용으로만 사용할 수 있습니다.");
  };

  const mergeLocalReview = (input: ReviewInput): ReviewMatrix => {
    const now = new Date().toISOString();
    const localReview: ReviewLog = {
      id: `local-${currentRole}-${input.criterion_item_id}`,
      criteria_version_id: versionId,
      application_id: reviewMatrix.application_id,
      criterion_item_id: input.criterion_item_id,
      reviewer_role: currentRole,
      status: input.status,
      reason_text: input.reason_text,
      source_location: input.source_location,
      created_at: now,
      updated_at: now,
    };
    const rows = reviewMatrix.rows.map((row) => {
      if (row.criterion_item_id !== input.criterion_item_id) return row;
      const hrReview = currentRole === "HR" ? localReview : row.hr_review;
      const hmReview = currentRole === "HM" ? localReview : row.hm_review;
      const differences = hrReview && hmReview
        ? [
            ...(hrReview.status !== hmReview.status ? ["상태"] : []),
            ...(normalizeSourceLocation(hrReview.source_location) !== normalizeSourceLocation(hmReview.source_location) ? ["원문 위치"] : []),
          ]
        : [];
      return {
        ...row,
        hr_review: hrReview,
        hm_review: hmReview,
        differences,
        conflict_status: differences.length ? "OPEN" as const : hrReview && hmReview ? "NONE" as const : "PENDING" as const,
      };
    });
    return { ...reviewMatrix, rows, open_conflict_count: rows.filter((row) => row.conflict_status === "OPEN").length };
  };

  const handleReviewSave = async (input: ReviewInput) => {
    setReviewError("");
    try {
      const updated = await saveReview(versionId, {
        application_id: reviewMatrix.application_id,
        reviewer_role: currentRole,
        reviews: [input],
      });
      setReviewMatrix(updated);
      setSavedMessage(`${ROLE_LABELS[currentRole]} 검토를 저장했습니다. 양쪽 의견은 자동으로 통합되지 않습니다.`);
    } catch (error) {
      if (isNetworkError(error)) {
        setReviewMatrix(mergeLocalReview(input));
        setSavedMessage(`${ROLE_LABELS[currentRole]} 검토를 로컬 데모에 저장했습니다.`);
      } else {
        setReviewError("검토 저장에 실패했습니다. 서버 응답을 확인한 뒤 다시 시도하세요.");
      }
    }
  };

  const mergeLocalResolution = (itemId: string, reason: string): ReviewMatrix => {
    const now = new Date().toISOString();
    const resolution: ConflictResolution = {
      id: `local-resolution-${itemId}`,
      criteria_version_id: versionId,
      application_id: reviewMatrix.application_id,
      criterion_item_id: itemId,
      status: "RESOLVED",
      resolved_by: "HR",
      resolved_at: now,
      resolution_reason: reason,
    };
    return {
      ...reviewMatrix,
      rows: reviewMatrix.rows.map((row) => row.criterion_item_id === itemId ? { ...row, conflict_status: "RESOLVED" as const, resolution } : row),
      open_conflict_count: reviewMatrix.rows.filter((row) => row.criterion_item_id !== itemId && row.conflict_status === "OPEN").length,
    };
  };

  const handleResolve = async (itemId: string, reason: string) => {
    if (!reason) return;
    setReviewError("");
    try {
      setReviewMatrix(await resolveConflict(versionId, { application_id: reviewMatrix.application_id, criterion_item_id: itemId, resolution_reason: reason }));
      setSavedMessage("충돌을 해결로 기록했습니다. 원래 HR/HM 판단과 근거는 보존됩니다.");
    } catch (error) {
      if (isNetworkError(error)) {
        setReviewMatrix(mergeLocalResolution(itemId, reason));
        setSavedMessage("충돌 해결을 로컬 데모에 기록했습니다. 원래 HR/HM 판단과 근거는 보존됩니다.");
      } else {
        setReviewError("충돌 해결에 실패했습니다. 서버 응답을 확인한 뒤 다시 시도하세요.");
      }
    }
  };

  const pendingReviewCount = reviewMatrix.rows.filter((row) => row.conflict_status === "PENDING").length;
  const canApprove = currentRole === "HR" && versionStatus === "DRAFT" && reviewMatrix.open_conflict_count === 0 && pendingReviewCount === 0;

  const handleApprove = async () => {
    if (!canApprove) {
      setReviewError(`승인 전 조건을 완료하세요: 열린 충돌 ${reviewMatrix.open_conflict_count}건 · 양쪽 검토 대기 ${pendingReviewCount}건`);
      return;
    }
    setReviewError("");
    try {
      const result = await approveCriteria(versionId, currentRole);
      setVersionStatus(result.version.status);
      setSavedMessage(`기준 버전 ${result.criteria_version_id}을 승인했습니다. 공식 핸드오프 잠금이 해제됩니다.`);
    } catch (error) {
      if (isNetworkError(error)) {
        setReviewError("서버에 연결되지 않아 기준 승인 상태를 확인하지 못했습니다. 연결 후 다시 시도하세요.");
      } else {
        setReviewError("기준 승인에 실패했습니다. 열린 충돌과 양쪽 검토 완료 여부를 확인하세요.");
      }
    }
  };

  const handleGenerateHandoff = async () => {
    try {
      const result = await generateHandoff(versionId);
      setSavedMessage(result.handoff_unlocked ? `공식 핸드오프를 열었습니다 · ${result.criteria_version_id}` : "공식 핸드오프가 잠겨 있습니다.");
    } catch {
      setReviewError("공식 핸드오프를 열지 못했습니다. 승인된 기준 버전과 서버 연결을 확인하세요.");
    }
  };

  const ROLE_LABELS: Record<ReviewerRole, string> = { HR: "HR", HM: "HM" };
  const officialUnlocked = versionStatus === "APPROVED";

  return (
    <main className="shell">
      <aside className="sidebar">
        <div className="brand-mark"><span className="brand-symbol">◈</span><span>Code.Presso</span></div>
        <div className="workspace-label">RECRUITING CONSOLE</div>
        <nav className="workflow-nav" aria-label="채용 워크플로우">
          <div className="nav-item active"><span className="nav-index">01</span><span>기준 교정</span><span className="nav-state">진행 중</span></div>
          <div className={`nav-item ${officialUnlocked ? "active" : "locked"}`}><span className="nav-index">02</span><span>지원서 검토</span><span className="nav-state">{officialUnlocked ? "사용 가능" : "잠김"}</span></div>
          <div className={`nav-item ${officialUnlocked ? "active" : "locked"}`}><span className="nav-index">03</span><span>현업 핸드오프</span><span className="nav-state">{officialUnlocked ? "사용 가능" : "잠김"}</span></div>
        </nav>
        <div className="sidebar-footer"><span className="avatar">H</span><span><strong>민지</strong><small>채용 담당자 · HR</small></span></div>
      </aside>
      <div className="content">
        <header className="topbar">
          <div><span className="breadcrumb">포지션 / 기준 교정</span><h1>B2B 영업 매니저</h1></div>
          <div className="context-bar"><span className="context-label">현재 기준</span><strong>{versionId}</strong><span className="top-status">{versionStatus}</span></div>
        </header>
        <div className="page-body">
          <GateBanner status={versionStatus} openConflicts={reviewMatrix.open_conflict_count} pendingReviews={pendingReviewCount} onGenerateHandoff={handleGenerateHandoff} />
          {savedMessage && <div className="live-message" role="status">✓ {savedMessage}</div>}
          {invalidated && <div className="invalidated-message"><strong>매핑 결과가 무효화되었습니다</strong><span>기준 문구가 변경되어 기존 근거를 공식 결과로 사용할 수 없습니다. 수정된 기준으로 파이프라인을 다시 실행하세요.</span><button type="button" onClick={() => setInvalidated(false)}>확인</button></div>}
          <div className="intro-row">
            <div><p className="eyebrow">CALIBRATION GATE · HR VIEW</p><h2>공식 검토 전에 기준을 맞춰보세요</h2><p>현재 적용될 기준과 버전을 확인하고, 리더 승인 전에는 결과를 탐색용으로 검토할 수 있습니다.</p></div>
            <div className="summary-card"><span>현재 버전</span><strong>{versionId}</strong><small>생성 2026. 08. 27 · 수정 {invalidated ? "방금 전" : "오늘 16:42"}</small></div>
          </div>
          <CriteriaVersionPanel versionId={versionId} status={versionStatus} updatedAt={invalidated ? "방금 전" : "오늘 16:42"} items={items} editing={editing} onToggleEditing={() => setEditing(true)} onChange={updateItem} onSave={saveChanges} onCreateVersion={createVersion} />
          {reviewLoading ? <div className="live-message" role="status">교정 표본을 불러오는 중…</div> : reviewLoadError ? <div className="invalidated-message" role="alert"><strong>교정 표본을 불러오지 못했습니다</strong><span>{reviewLoadError}</span></div> : <CalibrationMatrix matrix={reviewMatrix} currentRole={currentRole} onRoleChange={setCurrentRole} onSave={handleReviewSave} onResolve={handleResolve} />}
          {reviewError && <div className="invalidated-message" role="alert"><strong>작업을 완료하지 못했습니다</strong><span>{reviewError}</span></div>}
          <section className="approval-panel" aria-label="기준 버전 승인">
            {versionStatus === "APPROVED" ? <div className="live-message" role="status">✓ 승인 완료 · {versionId} · 공식 핸드오프 잠금 해제</div> : versionStatus === "ARCHIVED" ? <div className="live-message" role="status">보관된 기준 · {versionId} · 공식 핸드오프 잠김</div> : <><button className="button primary" type="button" onClick={handleApprove} disabled={!canApprove}>기준 승인</button><span className="approval-help">{canApprove ? "HR이 승인하면 공식 핸드오프 생성이 열립니다." : `승인 조건 · 열린 충돌 ${reviewMatrix.open_conflict_count}건 · 양쪽 검토 대기 ${pendingReviewCount}건`}</span></>}
          </section>
          <section className="preview-panel" aria-labelledby="preview-heading">
            <div className="panel-heading"><div><p className="eyebrow">EXPLORATION PREVIEW</p><h2 id="preview-heading">지원서 매핑 미리보기</h2></div><span className="preview-count">탐색용 1건</span></div>
            <div className="preview-row"><div className="applicant"><span className="document-icon">▤</span><span><strong>대표 지원자 · APPS-2</strong><small>원문 처리 완료 · 기준별 근거 확인 가능</small></span></div><span className="evidence-chip">근거 1건</span><span className={`preview-label ${previewStatus === "INVALIDATED" ? "invalidated-label" : ""}`}>{previewStatus === "INVALIDATED" ? "매핑 무효" : "미리보기"}</span><button className="text-button" type="button" onClick={() => setSavedMessage("지원서 매핑 미리보기는 승인 전 탐색 결과입니다.")}>결과 열기 <span aria-hidden="true">→</span></button></div>
            <div className="preview-note">ⓘ {previewStatus === "INVALIDATED" ? "기준 문구가 변경되어 기존 매핑은 무효화되었습니다. 재실행 후 다시 확인하세요." : "Draft 결과는 기준 합의 전 탐색용입니다. 공식 판단이나 핸드오프 카드에는 포함되지 않습니다."}</div>
          </section>
        </div>
      </div>
    </main>
  );
}

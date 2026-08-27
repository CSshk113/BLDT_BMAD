"use client";

import { useEffect, useState } from "react";
import React from "react";
import { CriteriaItem, CriteriaVersionPanel } from "@/components/criteria/CriteriaVersionPanel";
import { GateBanner } from "@/components/criteria/GateBanner";
import { createDraft, loadCriteria, loadPreview, saveDraft, toUiItems } from "@/lib/criteria-api";

const initialItems: CriteriaItem[] = [
  { id: "item-1", text: "콜드 아웃바운드 영업 경험", type: "필수" },
  { id: "item-2", text: "B2B 세일즈 파이프라인 운영 경험", type: "필수" },
  { id: "item-3", text: "CRM 또는 세일즈 데이터 기반 성과 관리", type: "우대" },
];

export default function CalibrationPage() {
  const [versionId, setVersionId] = useState("cv-b2b-sales-v4");
  const [items, setItems] = useState(initialItems);
  const [editing, setEditing] = useState(false);
  const [invalidated, setInvalidated] = useState(false);
  const [savedMessage, setSavedMessage] = useState("");
  const [previewStatus, setPreviewStatus] = useState<"COMPLETED" | "INVALIDATED">("COMPLETED");

  useEffect(() => {
    let active = true;
    Promise.all([loadCriteria(versionId), loadPreview(versionId)])
      .then(([criteriaResult, preview]) => {
        if (!active) return;
        setItems(criteriaResult.items);
        const mappingStatus = preview.mappings[0]?.mapping_status;
        if (mappingStatus === "INVALIDATED") {
          setPreviewStatus("INVALIDATED");
          setInvalidated(true);
        }
      })
      .catch(() => {
        // The static demo state remains usable when the API is not running yet.
      });
    return () => {
      active = false;
    };
  }, [versionId]);

  const updateItem = (id: string, value: string) => {
    setItems((current) => current.map((item) => (item.id === id ? { ...item, text: value } : item)));
  };

  const saveChanges = async () => {
    setEditing(false);
    try {
      const result = await saveDraft(versionId, items);
      setItems(toUiItems(result.version));
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
    } catch {
      setVersionId(`cv-b2b-sales-v4-draft-${Date.now().toString().slice(-4)}`);
    }
    setInvalidated(false);
    setPreviewStatus("COMPLETED");
    setSavedMessage("새 Draft 기준 버전을 만들었습니다. HM 승인 전까지 탐색용으로만 사용할 수 있습니다.");
  };

  return (
    <main className="shell">
      <aside className="sidebar">
        <div className="brand-mark"><span className="brand-symbol">◈</span><span>Code.Presso</span></div>
        <div className="workspace-label">RECRUITING CONSOLE</div>
        <nav className="workflow-nav" aria-label="채용 워크플로우">
          <div className="nav-item active"><span className="nav-index">01</span><span>기준 교정</span><span className="nav-state">진행 중</span></div>
          <div className="nav-item locked"><span className="nav-index">02</span><span>지원서 검토</span><span className="nav-state">잠김</span></div>
          <div className="nav-item locked"><span className="nav-index">03</span><span>현업 핸드오프</span><span className="nav-state">잠김</span></div>
        </nav>
        <div className="sidebar-footer"><span className="avatar">H</span><span><strong>민지</strong><small>채용 담당자 · HR</small></span></div>
      </aside>
      <div className="content">
        <header className="topbar">
          <div><span className="breadcrumb">포지션 / 기준 교정</span><h1>B2B 영업 매니저</h1></div>
          <div className="context-bar"><span className="context-label">현재 기준</span><strong>{versionId}</strong><span className="top-status">DRAFT</span></div>
        </header>
        <div className="page-body">
          <GateBanner openConflicts={3} />
          {savedMessage && <div className="live-message" role="status">✓ {savedMessage}</div>}
          {invalidated && <div className="invalidated-message"><strong>매핑 결과가 무효화되었습니다</strong><span>기준 문구가 변경되어 기존 근거를 공식 결과로 사용할 수 없습니다. 수정된 기준으로 파이프라인을 다시 실행하세요.</span><button type="button" onClick={() => setInvalidated(false)}>확인</button></div>}
          <div className="intro-row">
            <div><p className="eyebrow">CALIBRATION GATE · HR VIEW</p><h2>공식 검토 전에 기준을 맞춰보세요</h2><p>현재 적용될 기준과 버전을 확인하고, 리더 승인 전에는 결과를 탐색용으로 검토할 수 있습니다.</p></div>
            <div className="summary-card"><span>현재 버전</span><strong>{versionId}</strong><small>생성 2026. 08. 27 · 수정 {invalidated ? "방금 전" : "오늘 16:42"}</small></div>
          </div>
          <CriteriaVersionPanel versionId={versionId} status="DRAFT" updatedAt={invalidated ? "방금 전" : "오늘 16:42"} items={items} editing={editing} onToggleEditing={() => setEditing(true)} onChange={updateItem} onSave={saveChanges} onCreateVersion={createVersion} />
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

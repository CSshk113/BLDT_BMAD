import React from "react";

export type CriteriaItem = {
  id: string;
  text: string;
  type: "필수" | "우대";
};

type CriteriaVersionPanelProps = {
  versionId: string;
  status: "DRAFT" | "APPROVED";
  updatedAt: string;
  items: CriteriaItem[];
  editing: boolean;
  onToggleEditing: () => void;
  onChange: (id: string, value: string) => void;
  onSave: () => void;
  onCreateVersion: () => void;
};

export function CriteriaVersionPanel({
  versionId,
  status,
  updatedAt,
  items,
  editing,
  onToggleEditing,
  onChange,
  onSave,
  onCreateVersion,
}: CriteriaVersionPanelProps) {
  return (
    <section className="criteria-panel" aria-labelledby="criteria-heading">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">POSITION CRITERIA</p>
          <h2 id="criteria-heading">평가 기준</h2>
        </div>
        <div className="panel-actions">
          <button className="button secondary" type="button" onClick={onCreateVersion}>새 Draft 만들기</button>
          {editing ? (
            <button className="button primary" type="button" onClick={onSave}>변경 저장</button>
          ) : (
            <button className="button secondary" type="button" onClick={onToggleEditing}>기준 수정</button>
          )}
        </div>
      </div>
      <div className="version-meta">
        <span className="version-id">{versionId}</span>
        <span className={`status-pill ${status.toLowerCase()}`}>{status === "DRAFT" ? "미승인 · Draft" : "승인됨"}</span>
        <span className="updated">마지막 수정 {updatedAt}</span>
      </div>
      <div className="criteria-list">
        {items.map((item, index) => (
          <div className="criterion-row" key={item.id}>
            <span className="criterion-number">{String(index + 1).padStart(2, "0")}</span>
            <span className={`requirement-badge ${item.type === "필수" ? "required" : "preferred"}`}>{item.type}</span>
            {editing ? (
              <input
                aria-label={`${item.type} 기준 ${index + 1}`}
                className="criterion-input"
                value={item.text}
                onChange={(event) => onChange(item.id, event.target.value)}
              />
            ) : (
              <span className="criterion-text">{item.text}</span>
            )}
          </div>
        ))}
      </div>
      {editing && <p className="edit-help">기준 문구를 바꾸면 기존 매핑은 무효화되고 수정 기준으로 다시 실행해야 합니다.</p>}
    </section>
  );
}

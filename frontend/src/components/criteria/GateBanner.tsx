import React from "react";

type GateBannerProps = {
  status?: "DRAFT" | "APPROVED" | "ARCHIVED";
  openConflicts?: number;
  pendingReviews?: number;
  onGenerateHandoff?: () => void;
};

export function GateBanner({ status = "DRAFT", openConflicts = 3, pendingReviews = 0, onGenerateHandoff }: GateBannerProps) {
  const approved = status === "APPROVED";
  const archived = status === "ARCHIVED";
  return (
    <section className="gate-banner" aria-label="공식 기능 잠금 안내">
      <div className="gate-icon" aria-hidden="true">{approved ? "✓" : archived ? "—" : "!"}</div>
      <div>
        <strong>{approved ? "승인된 기준 · 공식 흐름 사용 가능" : archived ? "보관된 기준 · 공식 흐름 잠김" : "Draft 기준 · 탐색용 미리보기"}</strong>
        <p>{approved ? "승인된 기준 버전이 공식 핸드오프와 다음 결정 흐름에 연결됩니다." : archived ? "보관된 기준은 다시 승인하거나 공식 핸드오프에 사용할 수 없습니다." : "HM 검토와 충돌 해결 후 기준을 승인하면 공식 핸드오프가 열립니다."}</p>
        <span className="gate-detail">{approved ? "조건 완료: 기준 버전 승인 · 공식 핸드오프 잠금 해제" : archived ? "조건 완료 불가: 보관된 기준 버전" : `남은 조건: 양쪽 검토 대기 ${pendingReviews}건 · 열린 충돌 ${openConflicts}건 · 기준 승인`}</span>
      </div>
      <button className={approved ? "button primary" : "locked-button"} type="button" onClick={onGenerateHandoff} disabled={!approved} aria-disabled={!approved}>
        {approved ? "✓ 공식 핸드오프 열기" : "🔒 공식 핸드오프 잠김"}
      </button>
    </section>
  );
}

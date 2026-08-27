import React from "react";

type GateBannerProps = {
  openConflicts?: number;
};

export function GateBanner({ openConflicts = 3 }: GateBannerProps) {
  return (
    <section className="gate-banner" aria-label="공식 기능 잠금 안내">
      <div className="gate-icon" aria-hidden="true">!</div>
      <div>
        <strong>Draft 기준 · 탐색용 미리보기</strong>
        <p>HM 검토와 충돌 해결 후 기준을 승인하면 공식 핸드오프가 열립니다.</p>
        <span className="gate-detail">남은 조건: HM 검토 완료 · 열린 충돌 {openConflicts}건 · 기준 승인</span>
      </div>
      <button className="locked-button" type="button" disabled aria-disabled="true">
        🔒 공식 핸드오프 잠김
      </button>
    </section>
  );
}

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import CalibrationPage from "./page";

afterEach(() => vi.unstubAllGlobals());

describe("calibration page", () => {
  it("shows the active Draft criteria and official gate", () => {
    render(<CalibrationPage />);

    expect(screen.getAllByText("cv-b2b-sales-v4").length).toBeGreaterThan(0);
    expect(screen.getByText("미승인 · Draft")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /공식 핸드오프 잠김/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "기준 승인" })).toBeDisabled();
    expect(screen.getByText(/승인 조건 · 열린 충돌/)).toBeInTheDocument();
    expect(screen.getByText("지원서 매핑 미리보기")).toBeInTheDocument();
  });

  it("invalidates the preview mapping after a changed criterion is saved", async () => {
    render(<CalibrationPage />);
    fireEvent.click(screen.getByRole("button", { name: "기준 수정" }));
    const input = await screen.findByRole("textbox", { name: "필수 기준 1" });
    fireEvent.change(input, { target: { value: "새로운 콜드 아웃바운드 경험" } });
    fireEvent.click(screen.getByRole("button", { name: "변경 저장" }));

    expect(await screen.findByText("매핑 결과가 무효화되었습니다")).toBeInTheDocument();
  });

  it("renders criteria returned by the API when it is available", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      const payload = url.endsWith("/preview")
        ? { mappings: [{ mapping_status: "COMPLETED" }] }
        : {
            id: "cv-server",
            position_name: "B2B 영업 매니저 5년 이상 ver.4",
            status: "DRAFT",
            updated_at: "2026-08-27T00:00:00Z",
            items: [{ id: "server-item", criterion_text: "서버에서 받은 기준", requirement_type: "필수" }],
          };
      return Promise.resolve({ ok: true, json: async () => payload } as Response);
    }));

    render(<CalibrationPage />);

    await waitFor(() => expect(screen.getByText("서버에서 받은 기준")).toBeInTheDocument());
  });

  it("shows both reviewer opinions and keeps the other role read-only", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/conflicts")) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            criteria_version_id: "cv-b2b-sales-v4",
            application_id: "APPS-2",
            open_conflict_count: 1,
            rows: [{
              criterion_item_id: "server-item",
              criterion_text: "서버에서 받은 기준",
              requirement_type: "필수",
              conflict_status: "OPEN",
              differences: ["상태"],
              hr_review: { id: "hr-1", criteria_version_id: "cv-b2b-sales-v4", application_id: "APPS-2", criterion_item_id: "server-item", reviewer_role: "HR", status: "FULFILLED", reason_text: "HR 근거", source_location: "p.1", created_at: "2026-08-27T00:00:00Z", updated_at: "2026-08-27T00:00:00Z" },
              hm_review: { id: "hm-1", criteria_version_id: "cv-b2b-sales-v4", application_id: "APPS-2", criterion_item_id: "server-item", reviewer_role: "HM", status: "UNVERIFIABLE", reason_text: "HM 근거", source_location: "p.1", created_at: "2026-08-27T00:00:00Z", updated_at: "2026-08-27T00:00:00Z" },
            }],
          }),
        } as Response);
      }
      const payload = url.endsWith("/preview")
        ? { mappings: [{ mapping_status: "COMPLETED" }] }
        : {
            id: "cv-b2b-sales-v4",
            position_name: "B2B 영업 매니저 5년 이상 ver.4",
            status: "DRAFT",
            updated_at: "2026-08-27T00:00:00Z",
            items: [{ id: "server-item", criterion_text: "서버에서 받은 기준", requirement_type: "필수" }],
          };
      return Promise.resolve({ ok: true, json: async () => payload } as Response);
    }));

    render(<CalibrationPage />);

    expect(await screen.findByText("열린 충돌 1건")).toBeInTheDocument();
    expect(screen.getAllByText("HR 근거").length).toBeGreaterThan(0);
    expect(screen.getAllByText("HM 근거").length).toBeGreaterThan(0);
    expect(screen.getByText("차이: 상태")).toBeInTheDocument();
    expect(screen.getByText("다른 검토자의 기록은 읽기 전용으로 표시됩니다.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "독립 검토 저장" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "기준 승인" })).toBeDisabled();
    expect(screen.getByText("충돌 해결", { selector: "div" })).toBeInTheDocument();
  });
});

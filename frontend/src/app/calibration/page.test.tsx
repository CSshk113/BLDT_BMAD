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
});

"""Server-only LlamaParse boundary.

The application service depends on this small protocol, so tests can inject a
fake parser without ever putting a LlamaParse credential in the browser.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import time
from typing import Protocol
from urllib import error, request
import uuid


DEFAULT_MODEL = "llamaparse"


class ParserError(RuntimeError):
    """A parser call failed or returned an unusable document."""


class ParserConfigurationError(ParserError):
    """The server is missing the configuration required to call LlamaParse."""


@dataclass(frozen=True)
class ParsedDocument:
    markdown: str
    parser_model: str = DEFAULT_MODEL


class DocumentParser(Protocol):
    def parse(self, file_path: Path) -> ParsedDocument:
        ...


def normalize_markdown(markdown: str) -> str:
    """Make parser output stable while retaining the source text and headings."""
    normalized = markdown.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in normalized.split("\n")]
    result: list[str] = []
    blank_count = 0
    for line in lines:
        if line.strip():
            blank_count = 0
            result.append(line)
        elif blank_count < 1:
            blank_count += 1
            result.append("")
    return "\n".join(result).strip() + ("\n" if result else "")


class LlamaParseAdapter:
    """Minimal HTTP adapter using only server environment configuration."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("LLAMAPARSE_API_KEY")
        self.base_url = (base_url or os.getenv("LLAMAPARSE_BASE_URL") or "https://api.cloud.llamaindex.ai").rstrip("/")
        self.timeout_seconds = timeout_seconds or float(os.getenv("LLAMAPARSE_TIMEOUT_SECONDS", "60"))

    def parse(self, file_path: Path) -> ParsedDocument:
        if not self.api_key:
            raise ParserConfigurationError(
                "LlamaParse가 설정되지 않았습니다. 서버의 LLAMAPARSE_API_KEY를 확인하세요."
            )
        if not file_path.is_file():
            raise ParserError("원본 PDF를 찾을 수 없습니다")

        boundary = f"----CodexLlamaParse{uuid.uuid4().hex}"
        body = self._multipart_body(boundary, file_path)
        upload_request = request.Request(
            f"{self.base_url}/api/parsing/upload",
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Accept": "application/json",
            },
        )
        try:
            with request.urlopen(upload_request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, error.HTTPError, json.JSONDecodeError) as exc:
            raise ParserError(f"LlamaParse 요청에 실패했습니다: {exc}") from exc

        markdown = self._find_markdown(payload)
        if markdown is not None:
            return ParsedDocument(markdown=markdown)
        job_id = payload.get("id") or payload.get("job_id") or payload.get("jobId")
        if not job_id:
            raise ParserError("LlamaParse 응답에 변환 결과 또는 작업 ID가 없습니다")
        return self._poll_result(str(job_id))

    @staticmethod
    def _multipart_body(boundary: str, file_path: Path) -> bytes:
        content = file_path.read_bytes()
        header = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"\r\n'
            "Content-Type: application/pdf\r\n\r\n"
        ).encode("utf-8")
        return header + content + f"\r\n--{boundary}--\r\n".encode("utf-8")

    def _poll_result(self, job_id: str) -> ParsedDocument:
        deadline = time.monotonic() + self.timeout_seconds
        result_url = f"{self.base_url}/api/parsing/job/{job_id}/result/markdown"
        while time.monotonic() < deadline:
            result_request = request.Request(
                result_url,
                method="GET",
                headers={"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"},
            )
            try:
                with request.urlopen(result_request, timeout=min(10, self.timeout_seconds)) as response:
                    raw = response.read().decode("utf-8")
                    payload = json.loads(raw)
            except error.HTTPError as exc:
                if exc.code in {202, 404}:
                    time.sleep(0.2)
                    continue
                raise ParserError(f"LlamaParse 결과 조회에 실패했습니다: HTTP {exc.code}") from exc
            except (OSError, json.JSONDecodeError) as exc:
                raise ParserError(f"LlamaParse 결과 조회에 실패했습니다: {exc}") from exc
            markdown = self._find_markdown(payload)
            if markdown is not None:
                return ParsedDocument(markdown=markdown)
            time.sleep(0.2)
        raise ParserError("LlamaParse 변환 시간이 초과되었습니다")

    @staticmethod
    def _find_markdown(payload: object) -> str | None:
        if isinstance(payload, str) and payload.strip():
            return payload
        if not isinstance(payload, dict):
            return None
        for key in ("markdown", "text", "content"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value
        nested = payload.get("result")
        if isinstance(nested, dict):
            return LlamaParseAdapter._find_markdown(nested)
        return None

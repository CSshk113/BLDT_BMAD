from pathlib import Path
import json

from backend.app.services import llamaparse


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_adapter_uploads_pdf_and_extracts_markdown(tmp_path: Path, monkeypatch):
    pdf = tmp_path / "resume.pdf"
    pdf.write_bytes(b"%PDF-1.7 demo")
    requests = []

    def fake_urlopen(request, timeout):
        requests.append((request, timeout))
        return FakeResponse({"result": {"markdown": "# parsed resume"}})

    monkeypatch.setattr(llamaparse.request, "urlopen", fake_urlopen)

    result = llamaparse.LlamaParseAdapter(api_key="test-key", base_url="https://parser.test").parse(pdf)

    assert result.markdown == "# parsed resume"
    assert requests[0][0].full_url == "https://parser.test/api/parsing/upload"
    assert requests[0][0].get_header("Authorization") == "Bearer test-key"
    assert b"%PDF-1.7 demo" in requests[0][0].data

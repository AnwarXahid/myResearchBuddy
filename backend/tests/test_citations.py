import httpx

from app.citations import CitationVerifier


def test_citation_verifier_handles_http_error(monkeypatch):
    def raise_error(*args, **kwargs):
        raise httpx.HTTPError("boom")

    monkeypatch.setattr(httpx.Client, "get", raise_error)
    verifier = CitationVerifier()
    result = verifier.verify("Test Title")
    assert result["status"] == "unverified"

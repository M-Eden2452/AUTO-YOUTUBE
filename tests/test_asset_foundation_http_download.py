from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import requests


class FakeResponse:
    def __init__(
        self,
        *,
        status_code: int = 200,
        json_data: dict | None = None,
        headers: dict[str, str] | None = None,
        chunks: list[bytes] | None = None,
        raise_during_iter: bool = False,
    ) -> None:
        self.status_code = status_code
        self._json_data = json_data or {}
        self.headers = headers or {}
        self._chunks = chunks or []
        self.raise_during_iter = raise_during_iter

    def json(self) -> dict:
        return self._json_data

    def iter_content(self, chunk_size: int = 8192):
        for index, chunk in enumerate(self._chunks):
            if self.raise_during_iter and index == 1:
                raise requests.ConnectionError("stream interrupted")
            yield chunk

    def close(self) -> None:
        return None


class FlakySession:
    def __init__(self, responses: list[object]) -> None:
        self.responses = list(responses)
        self.calls = 0

    def request(self, method: str, url: str, **kwargs):
        self.calls += 1
        item = self.responses.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


class AssetHttpDownloadTests(unittest.TestCase):
    def test_http_client_retries_timeout_429_and_5xx_then_returns_json(self) -> None:
        from src.assets.http_client import ProviderHttpClient

        session = FlakySession(
            [
                requests.Timeout("slow"),
                FakeResponse(status_code=429, headers={"Retry-After": "0"}),
                FakeResponse(status_code=502),
                FakeResponse(status_code=200, json_data={"ok": True}),
            ]
        )
        sleeps: list[float] = []
        client = ProviderHttpClient(session=session, max_retries=4, backoff_base=0, sleep=sleeps.append)

        data = client.get_json("https://example.test/search")

        self.assertEqual(data, {"ok": True})
        self.assertEqual(session.calls, 4)
        self.assertGreaterEqual(len(sleeps), 3)

    def test_http_client_does_not_retry_auth_errors(self) -> None:
        from src.assets.http_client import ProviderHttpClient
        from src.assets.provider_contract import ProviderAuthenticationError

        session = FlakySession([FakeResponse(status_code=401), FakeResponse(status_code=200, json_data={"unexpected": True})])
        client = ProviderHttpClient(session=session, max_retries=3, backoff_base=0, sleep=lambda _seconds: None)

        with self.assertRaises(ProviderAuthenticationError):
            client.get_json("https://example.test/search")

        self.assertEqual(session.calls, 1)

    def test_stream_download_cleans_part_file_and_sha256s_success(self) -> None:
        from src.assets.http_client import ProviderHttpClient
        from src.assets.provider_contract import ProviderDownloadError

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "clip.bin"
            failing = FlakySession(
                [
                    FakeResponse(
                        status_code=200,
                        headers={"Content-Type": "video/mp4", "Content-Length": "6"},
                        chunks=[b"abc", b"def"],
                        raise_during_iter=True,
                    )
                ]
            )
            client = ProviderHttpClient(session=failing, max_retries=1, backoff_base=0, sleep=lambda _seconds: None)

            with self.assertRaises(ProviderDownloadError):
                client.download_stream("https://example.test/file.mp4", target, allowed_content_types={"video/mp4"}, min_bytes=1)

            self.assertFalse(target.exists())
            self.assertFalse(target.with_suffix(target.suffix + ".part").exists())

            success = FlakySession(
                [
                    FakeResponse(
                        status_code=200,
                        headers={"Content-Type": "video/mp4", "Content-Length": "6"},
                        chunks=[b"abc", b"def"],
                    )
                ]
            )
            client = ProviderHttpClient(session=success, max_retries=1, backoff_base=0, sleep=lambda _seconds: None)
            result = client.download_stream("https://example.test/file.mp4", target, allowed_content_types={"video/mp4"}, min_bytes=1)

            self.assertTrue(target.is_file())
            self.assertEqual(result["bytes"], 6)
            self.assertEqual(len(result["checksum_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()


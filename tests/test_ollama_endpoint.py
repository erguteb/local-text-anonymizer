from __future__ import annotations

import json
import unittest
import urllib.error
from unittest.mock import patch

import main


class TestOllamaEndpointMessaging(unittest.TestCase):
    def test_guidance_mentions_configured_endpoint_and_default_local_example(self):
        message = main.format_ollama_endpoint_guidance("http://10.0.0.5:11434")
        self.assertIn("http://10.0.0.5:11434", message)
        self.assertIn(
            "http://127.0.0.1:11434 is only correct if a local Ollama server is running there",
            message,
        )
        self.assertIn("--ollama-base-url", message)

    def test_ollama_generate_uses_configured_endpoint_in_error(self):
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("boom")):
            with self.assertRaises(RuntimeError) as ctx:
                main.ollama_generate(
                    base_url="http://10.0.0.5:11434",
                    model="qwen3.5:latest",
                    prompt="test",
                    num_predict=8,
                )
        message = str(ctx.exception)
        self.assertIn("Failed to reach Ollama at http://10.0.0.5:11434", message)
        self.assertIn("Configured request URL: http://10.0.0.5:11434/api/generate", message)
        self.assertIn(
            "http://127.0.0.1:11434 is only correct if a local Ollama server is running there",
            message,
        )

    def test_ollama_list_models_parses_tags_response(self):
        class _FakeHttpResponse:
            def __init__(self, payload: dict) -> None:
                self._raw = json.dumps(payload).encode("utf-8")

            def read(self) -> bytes:
                return self._raw

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        with patch(
            "urllib.request.urlopen",
            return_value=_FakeHttpResponse({"models": [{"name": "qwen3.5:latest"}]}),
        ):
            names = main.ollama_list_models(base_url="http://10.0.0.5:11434")
        self.assertEqual(names, ["qwen3.5:latest"])


if __name__ == "__main__":
    unittest.main()

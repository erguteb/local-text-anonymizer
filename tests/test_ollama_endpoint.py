from __future__ import annotations

import json
import pathlib
import sys
import unittest
import urllib.error
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import main


class TestOllamaEndpointMessaging(unittest.TestCase):
    def test_parser_supports_output_audit_json_flag(self):
        args = main.build_arg_parser().parse_args(["--output-audit-json"])
        self.assertTrue(args.output_audit_json)

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

    def test_hf_cache_check_reports_missing_models(self):
        with patch("main.cached_file", return_value=None):
            present, missing = main.check_local_hf_model_cache(
                ["jxm/gtr__nq__32", "t5-base"],
                cache_dir="/tmp/hf-cache",
            )
        self.assertEqual(present, [])
        self.assertEqual(missing, ["jxm/gtr__nq__32", "t5-base"])

    def test_vec2text_asset_guidance_mentions_local_cache_and_missing_models(self):
        message = main.format_vec2text_asset_guidance(
            missing_model_ids=["jxm/gtr__nq__32", "t5-base"],
            cache_dir="/tmp/hf-cache",
        )
        self.assertIn("Missing local cache entries: jxm/gtr__nq__32, t5-base", message)
        self.assertIn("Checked cache: /tmp/hf-cache", message)
        self.assertIn("full anonymization path", message)


if __name__ == "__main__":
    unittest.main()

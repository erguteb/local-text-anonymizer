from __future__ import annotations

import pathlib
import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import main


class TestPreprocessPrivacyText(unittest.TestCase):
    def test_category_level_removals_are_expanded_and_scrubbed_before_dp(self):
        processed = main.preprocess_privacy_text(
            "I’m 23 and John Smith moved to Shoreditch for work in London.",
            keywords=["London", "restaurant"],
            removal_targets=["all names", "age", "Shoreditch"],
            max_privacy_chunks=3,
        )
        self.assertIn("[AGE]", processed.scrubbed_text)
        self.assertIn("[PERSON]", processed.scrubbed_text)
        self.assertIn("somewhere", processed.scrubbed_text)
        self.assertIn("London", processed.scrubbed_text)
        self.assertEqual(processed.expanded_removal_targets, ["[PERSON]", "[AGE]", "Shoreditch"])

    def test_privacy_chunking_limits_release_count(self):
        processed = main.preprocess_privacy_text(
            "One. Two. Three. Four. Five.",
            keywords=[],
            removal_targets=[],
            max_privacy_chunks=2,
        )
        self.assertLessEqual(len(processed.residual_segments), 2)


class TestAuditSummary(unittest.TestCase):
    def test_build_output_audit_summary_reflects_privacy_layers(self):
        processed = main.preprocess_privacy_text(
            "I’m 23 and John Smith moved to Shoreditch for work in London.",
            keywords=["London", "restaurant"],
            removal_targets=["all names", "age", "Shoreditch"],
            max_privacy_chunks=2,
        )
        accountant = main.estimate_metric_dp_privacy_cost(
            num_releases=len(processed.residual_segments),
            sigma=0.15,
            delta=1e-3,
            sensitivity=1.0,
        )
        summary = main.build_output_audit_summary(
            preprocessed=processed,
            accountant=accountant,
            fallback_triggered=True,
            llm_backend="ollama",
            sigma=0.15,
        )
        self.assertTrue(summary.local_only)
        self.assertTrue(summary.layer1_deterministic_scrub_before_embedding)
        self.assertTrue(summary.layer2_public_slots_outside_dp)
        self.assertTrue(summary.layer3_residual_only_dp_scope)
        self.assertTrue(summary.dp_accounting_reported)
        self.assertTrue(summary.deterministic_fallback_present)
        self.assertTrue(any("Ollama" in item for item in summary.remaining_limitations))

    def test_build_output_audit_summary_reports_pipeline_capabilities_even_without_trigger(self):
        processed = main.preprocess_privacy_text(
            "Generic request without explicit removals.",
            keywords=[],
            removal_targets=[],
            max_privacy_chunks=2,
        )
        accountant = main.estimate_metric_dp_privacy_cost(
            num_releases=len(processed.residual_segments),
            sigma=0.15,
            delta=1e-3,
            sensitivity=1.0,
        )
        summary = main.build_output_audit_summary(
            preprocessed=processed,
            accountant=accountant,
            fallback_triggered=False,
            llm_backend="ollama",
            sigma=0.15,
        )
        self.assertTrue(summary.layer1_deterministic_scrub_before_embedding)
        self.assertTrue(summary.layer2_public_slots_outside_dp)
        self.assertTrue(summary.deterministic_fallback_present)

    def test_output_audit_summary_to_dict_is_json_ready(self):
        summary = main.OutputAuditSummary(
            local_only=True,
            layer1_deterministic_scrub_before_embedding=True,
            layer2_public_slots_outside_dp=False,
            layer3_residual_only_dp_scope=True,
            dp_accounting_reported=True,
            deterministic_fallback_present=False,
            remaining_limitations=["test limitation"],
        )
        payload = main.output_audit_summary_to_dict(summary)
        self.assertEqual(
            payload,
            {
                "local_only": True,
                "layer1_deterministic_scrub_before_embedding": True,
                "layer2_public_slots_outside_dp": False,
                "layer3_residual_only_dp_scope": True,
                "dp_accounting_reported": True,
                "deterministic_fallback_present": False,
                "remaining_limitations": ["test limitation"],
            },
        )

    def test_main_outputs_audit_summary_json(self):
        preprocessed = main.PreprocessedPrivacyText(
            original_text="private text",
            scrubbed_text="scrubbed text",
            residual_text="residual text",
            expanded_removal_targets=[],
            preserved_keywords=[],
            safe_task_keywords=[],
            safe_location_keywords=[],
            safe_preference_keywords=[],
            residual_segments=["residual text"],
        )
        sentence_result = main.AnonymizationResult(
            anonymized_text="anonymized residual",
            mixed_target_embedding=main.torch.zeros((1, 2)),
            noisy_embedding=main.torch.zeros((1, 2)),
            clean_embedding=main.torch.zeros((1, 2)),
            keyword_embeddings=None,
        )
        sentence_wise = main.SentenceWiseAnonymizationResult(
            anonymized_text="anonymized residual",
            sentence_results=[sentence_result],
            source_sentences=["residual text"],
        )
        paraphrase_result = main.ParaphraseResult(
            model_name="qwen3.5:latest",
            model_type="ollama",
            input_text="anonymized residual",
            paraphrased_text="stable paraphrase",
        )

        argv = [
            "main.py",
            "--text",
            "private text",
            "--llm-backend",
            "ollama",
            "--no-interactive-removal",
            "--skip-embedding-checks",
            "--skip-baseline",
            "--output-audit-json",
        ]

        stdout = io.StringIO()
        with patch.object(sys, "argv", argv):
            with patch("main.preprocess_privacy_text", return_value=preprocessed):
                with patch("main.patch_transformers_constrained_beamsearch_4372", return_value=None):
                    with patch("main.load_vec2text_corrector", return_value=object()):
                        with patch(
                            "main.anonymize_localized_sentence_wise",
                            return_value=sentence_wise,
                        ):
                            with patch(
                                "main.paraphrase_with_open_source_llm",
                                return_value=paraphrase_result,
                            ):
                                with patch(
                                    "main.build_fused_fallback_output",
                                    side_effect=["without fusion", "with fusion"],
                                ):
                                    with patch(
                                        "main.looks_like_quality_collapse",
                                        return_value=False,
                                    ):
                                        with redirect_stdout(stdout):
                                            main.main()

        output = stdout.getvalue()
        self.assertIn("--- Output audit summary (json) ---", output)
        json_block = output.split("--- Output audit summary (json) ---", 1)[1].strip()
        json_text = json_block.split("\n\n---", 1)[0].strip()
        payload = json.loads(json_text)
        self.assertTrue(payload["local_only"])
        self.assertTrue(payload["layer1_deterministic_scrub_before_embedding"])
        self.assertTrue(payload["layer2_public_slots_outside_dp"])
        self.assertTrue(payload["layer3_residual_only_dp_scope"])
        self.assertTrue(payload["dp_accounting_reported"])
        self.assertTrue(payload["deterministic_fallback_present"])


class TestRewriteGuards(unittest.TestCase):
    def test_detects_unapproved_numbers(self):
        self.assertTrue(
            main.violates_local_rewrite_constraints(
                "I feel bad in London.",
                "I feel bad in London for 40 days.",
                keywords=["London"],
            )
        )

    def test_detects_unapproved_capitalized_entities(self):
        self.assertTrue(
            main.violates_local_rewrite_constraints(
                "I feel bad in London.",
                "I feel bad in London and Paris.",
                keywords=["London"],
            )
        )

    def test_detects_unapproved_location_terms(self):
        self.assertTrue(
            main.violates_local_rewrite_constraints(
                "I feel bad and want a restaurant tonight.",
                "I feel bad and want a restaurant tonight in Shoreditch.",
                keywords=["restaurant"],
            )
        )


class TestTemplateFallback(unittest.TestCase):
    def test_builds_template_from_scrubbed_text_and_keywords(self):
        processed = main.preprocess_privacy_text(
            "I’m [AGE], just moved to London for work after a breakup. I want a cozy restaurant tonight where dining alone feels comfortable.",
            keywords=["restaurant", "UK", "London", "cozy", "solo dining"],
            removal_targets=[],
            max_privacy_chunks=2,
        )
        output = main.build_template_fallback_output(
            preprocessed=processed,
            keywords=processed.preserved_keywords,
            residual_summary=processed.residual_text,
        )
        self.assertIn("Context:", output)
        self.assertIn("Request:", output)
        self.assertIn("Task: restaurant, solo dining", output)
        self.assertIn("Location: UK, London", output)
        self.assertIn("Preferences: cozy", output)
        self.assertIn("London for work", output)
        self.assertIn("cozy restaurant tonight", output)

    def test_fusion_accepts_safe_aligned_fragment_for_context_request(self):
        processed = main.preprocess_privacy_text(
            "I’m [AGE], just moved to London for work after a breakup. I want a cozy restaurant tonight where dining alone feels comfortable.",
            keywords=["restaurant", "UK", "London", "cozy", "solo dining"],
            removal_targets=[],
            max_privacy_chunks=2,
        )
        output = main.build_fused_fallback_output(
            preprocessed=processed,
            keywords=processed.preserved_keywords,
            residual_summary=processed.residual_text,
            candidate_text=(
                "I just moved to London for work after a breakup. "
                "I want a cozy restaurant tonight where dining alone feels comfortable."
            ),
        )
        self.assertIn("Context: I just moved to London for work after a breakup", output)
        self.assertIn("Request: I want a cozy restaurant tonight where dining alone feels comfortable.", output)

    def test_output_without_public_fusion_omits_slot_fields(self):
        processed = main.preprocess_privacy_text(
            "I’m [AGE], just moved to London for work after a breakup. I want a cozy restaurant tonight where dining alone feels comfortable.",
            keywords=["restaurant", "UK", "London", "cozy", "solo dining"],
            removal_targets=[],
            max_privacy_chunks=2,
        )
        output = main.build_fused_fallback_output(
            preprocessed=processed,
            keywords=processed.preserved_keywords,
            residual_summary=processed.residual_text,
            candidate_text=(
                "I just moved for work after a breakup. "
                "I want a place tonight where dining alone feels comfortable."
            ),
            include_public_fusion=False,
        )
        self.assertIn("Context:", output)
        self.assertIn("Request:", output)
        self.assertNotIn("Task:", output)
        self.assertNotIn("Location:", output)
        self.assertNotIn("Preferences:", output)
        self.assertNotIn("London", output)
        self.assertNotIn("restaurant", output)

    def test_output_with_public_fusion_reinserts_slot_fields(self):
        processed = main.preprocess_privacy_text(
            "I’m [AGE], just moved to London for work after a breakup. I want a cozy restaurant tonight where dining alone feels comfortable.",
            keywords=["restaurant", "UK", "London", "cozy", "solo dining"],
            removal_targets=[],
            max_privacy_chunks=2,
        )
        output = main.build_fused_fallback_output(
            preprocessed=processed,
            keywords=processed.preserved_keywords,
            residual_summary=processed.residual_text,
            candidate_text=(
                "I just moved to London for work after a breakup. "
                "I want a cozy restaurant tonight where dining alone feels comfortable."
            ),
            include_public_fusion=True,
        )
        self.assertIn("Task: restaurant, solo dining", output)
        self.assertIn("Location: UK, London", output)
        self.assertIn("Preferences: cozy", output)

    def test_fusion_rejects_nonsense_and_keeps_deterministic_floor(self):
        processed = main.preprocess_privacy_text(
            "I’m [AGE], just moved to London for work after a breakup. I want a cozy restaurant tonight where dining alone feels comfortable.",
            keywords=["restaurant", "UK", "London", "cozy", "solo dining"],
            removal_targets=[],
            max_privacy_chunks=2,
        )
        output = main.build_fused_fallback_output(
            preprocessed=processed,
            keywords=processed.preserved_keywords,
            residual_summary=processed.residual_text,
            candidate_text="A cookedolin' pity attacks around a microphone.",
        )
        self.assertNotIn("microphone", output)
        self.assertNotIn("cookedolin", output)
        self.assertIn("London for work", output)
        self.assertIn("cozy restaurant tonight", output)


if __name__ == "__main__":
    unittest.main()

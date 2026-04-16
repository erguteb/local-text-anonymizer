from __future__ import annotations

import pathlib
import sys
import unittest

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

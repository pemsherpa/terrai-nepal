from django.test import TestCase

from .vision import build_vision_explanation


class VisionExplanationTests(TestCase):
    def test_decline_explanation_is_explicit_about_proxy_mode(self):
        explanation = build_vision_explanation(
            ndvi_before=0.7,
            ndvi_after=0.5,
            change_pct=-28.57,
            evi_before=0.4,
            evi_after=0.25,
            rvi_before=0.8,
            rvi_after=0.6,
        )

        self.assertEqual(explanation["inference_mode"], "transparent-index-proxy")
        label = explanation["inference_label"].lower()
        self.assertTrue("weights not active" in label or "prototype weights trained" in label)
        self.assertEqual(explanation["prediction"], "Likely vegetation decline")
        self.assertEqual(len(explanation["models"]), 4)
        self.assertEqual(len(explanation["feature_evidence"]), 3)

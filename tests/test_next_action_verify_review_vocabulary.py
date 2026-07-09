import unittest

from video_pipeline_core.next_action_vocabulary import NEXT_ACTION_VOCABULARY


VERIFY_TOKENS = {"verify", "verified", "verification", "qa", "gate"}
REVIEW_TOKENS = {"review", "reviewed", "human"}


GRANDFATHERED_VERIFY_REVIEW_COMPOUNDS: set[str] = {
    "write_delivery_gate_report_or_review_highlight_candidate",
}


def _has_token(part: str, tokens: set[str]) -> bool:
    words = set(part.split("_"))
    return bool(words & tokens)


class NextActionVerifyReviewVocabularyTest(unittest.TestCase):
    def test_no_new_verify_or_review_compound_next_actions(self):
        offenders = []
        for action in sorted(NEXT_ACTION_VOCABULARY):
            if "_or_" not in action:
                continue
            parts = action.split("_or_")
            has_verify_side = any(_has_token(part, VERIFY_TOKENS) for part in parts)
            has_review_side = any(_has_token(part, REVIEW_TOKENS) for part in parts)
            if has_verify_side and has_review_side:
                offenders.append(action)

        new_offenders = sorted(set(offenders) - GRANDFATHERED_VERIFY_REVIEW_COMPOUNDS)
        self.assertEqual(
            new_offenders,
            [],
            "New next_action values must not combine verify-type and review-type "
            f"tokens across '_or_'; freeze only existing offenders. New offenders: {new_offenders}",
        )


if __name__ == "__main__":
    unittest.main()

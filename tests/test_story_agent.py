import json
import unittest

from story_agent import (
    STATUS_COMPLETED_WITH_WARNINGS,
    STATUS_FAILED_JUDGE,
    STATUS_PASSED,
    STATUS_REFUSED_SCOPE,
    run_story_agent,
)


def judgment(
    *,
    safe=True,
    quality=True,
    overall=4.5,
    language=4,
    creativity=4,
    bedtime=4,
    instructions="No revision needed.",
):
    return json.dumps(
        {
            "age_appropriate": safe,
            "safe_for_bedtime": safe,
            "no_unsafe_content": safe,
            "follows_request": quality,
            "has_story_arc": quality,
            "appropriate_length": quality,
            "language_score": language,
            "creativity_score": creativity,
            "bedtime_score": bedtime,
            "overall_score": overall,
            "issues": [] if safe and quality else ["Needs improvement."],
            "revision_instructions": instructions,
        }
    )


class FakeModel:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, messages, max_tokens=3000, temperature=0.7):
        self.calls.append(
            {
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
        )
        if not self.responses:
            raise AssertionError("FakeModel received more calls than expected.")
        return self.responses.pop(0)


class StoryAgentTests(unittest.TestCase):
    def test_passing_story_returns_after_first_candidate(self):
        model = FakeModel(["A cozy dragon story.", judgment()])

        result = run_story_agent("Tell me about a sleepy dragon.", model_client=model)

        self.assertEqual(result.status, STATUS_PASSED)
        self.assertEqual(result.story, "A cozy dragon story.")
        self.assertEqual(result.attempts_used, 1)
        self.assertEqual(len(model.calls), 2)

    def test_low_quality_story_triggers_revision_and_passes(self):
        model = FakeModel(
            [
                "A thin first draft.",
                judgment(
                    quality=False,
                    overall=3.2,
                    language=3,
                    creativity=3,
                    bedtime=4,
                    instructions="Add more story arc and warmth.",
                ),
                "A warmer revised story.",
                judgment(),
            ]
        )

        result = run_story_agent("Tell me about friends sharing the moon.", model_client=model)

        self.assertEqual(result.status, STATUS_PASSED)
        self.assertEqual(result.story, "A warmer revised story.")
        self.assertEqual(result.attempts_used, 2)

    def test_safety_failure_triggers_fallback(self):
        model = FakeModel(
            [
                "Unsafe draft.",
                judgment(safe=False, quality=False, overall=2.0),
                "Unsafe revision one.",
                judgment(safe=False, quality=False, overall=2.0),
                "Unsafe revision two.",
                judgment(safe=False, quality=False, overall=2.0),
                "A safe fallback animal story.",
                judgment(safe=True, quality=False, overall=3.5),
            ]
        )

        result = run_story_agent("Tell me a spooky story about a dragon.", model_client=model)

        self.assertEqual(result.status, STATUS_PASSED)
        self.assertEqual(result.story, "A safe fallback animal story.")
        self.assertTrue(result.used_fallback)
        self.assertEqual(result.attempts_used, 4)

    def test_invalid_judge_json_retries_once_and_succeeds(self):
        model = FakeModel(["A cozy story.", "not-json", judgment()])

        result = run_story_agent("Tell me about a moon rabbit.", model_client=model)

        self.assertEqual(result.status, STATUS_PASSED)
        self.assertEqual(result.story, "A cozy story.")
        self.assertEqual(result.attempts_used, 1)
        self.assertEqual(len(model.calls), 3)

    def test_invalid_judge_json_twice_fails_closed(self):
        model = FakeModel(["A cozy story.", "not-json", "still not json"])

        result = run_story_agent("Tell me about a moon rabbit.", model_client=model)

        self.assertEqual(result.status, STATUS_FAILED_JUDGE)
        self.assertIsNone(result.story)
        self.assertEqual(result.attempts_used, 1)

    def test_quality_failure_returns_best_safe_story(self):
        model = FakeModel(
            [
                "Safe but weak story.",
                judgment(quality=False, overall=3.2, language=3, creativity=3, bedtime=4),
                "Best safe story.",
                judgment(quality=False, overall=3.9, language=3, creativity=4, bedtime=4),
                "Later but weaker safe story.",
                judgment(quality=False, overall=3.4, language=3, creativity=3, bedtime=4),
            ]
        )

        result = run_story_agent("Tell me a gentle learning story.", model_client=model)

        self.assertEqual(result.status, STATUS_COMPLETED_WITH_WARNINGS)
        self.assertEqual(result.story, "Best safe story.")
        self.assertEqual(result.final_judgment["overall_score"], 3.9)

    def test_out_of_scope_request_refuses_without_model_calls(self):
        model = FakeModel([])

        result = run_story_agent("Write violent horror for a 5-year-old.", model_client=model)

        self.assertEqual(result.status, STATUS_REFUSED_SCOPE)
        self.assertIsNone(result.story)
        self.assertEqual(model.calls, [])

    def test_weird_but_harmless_request_is_accepted(self):
        model = FakeModel(["A ninja robot space story.", judgment()])

        result = run_story_agent("Tell me a story about a ninja robot in space.", model_client=model)

        self.assertEqual(result.status, STATUS_PASSED)
        self.assertEqual(result.story, "A ninja robot space story.")
        self.assertGreater(len(model.calls), 0)


if __name__ == "__main__":
    unittest.main()

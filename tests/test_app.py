import unittest

from bedtime_story_agent.domain.enums import StoryStatus
from bedtime_story_agent.domain.models import StoryResult
from bedtime_story_agent.web.app import create_app


class FakeRunner:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def __call__(self, user_request, debug=False, model="gpt-3.5-turbo"):
        self.calls.append(
            {
                "user_request": user_request,
                "debug": debug,
                "model": model,
            }
        )
        return self.result


class FlaskAppTests(unittest.TestCase):
    def make_client(self, runner):
        app = create_app(agent_runner=runner)
        app.config["TESTING"] = True
        return app.test_client()

    def test_get_renders_story_form(self):
        runner = FakeRunner(None)
        client = self.make_client(runner)

        response = client.get("/")

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Bedtime Story Agent", html)
        self.assertIn("gpt-3.5-turbo", html)
        self.assertIn("gpt-4o-mini", html)

    def test_post_renders_story_and_passes_selected_model(self):
        runner = FakeRunner(
            StoryResult(
                status=StoryStatus.PASSED,
                story="A cozy moon story.",
                final_judgment={"overall_score": 4.5},
                attempts_used=1,
            )
        )
        client = self.make_client(runner)

        response = client.post(
            "/",
            data={
                "request": "Tell me about a moon rabbit.",
                "model": "gpt-4o-mini",
            },
        )

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("A cozy moon story.", html)
        self.assertEqual(runner.calls[0]["model"], "gpt-4o-mini")
        self.assertEqual(runner.calls[0]["user_request"], "Tell me about a moon rabbit.")

    def test_post_renders_refusal_safely(self):
        runner = FakeRunner(
            StoryResult(
                status=StoryStatus.REFUSED_SCOPE,
                story=None,
                final_judgment=None,
                attempts_used=0,
                warnings=["I can only create bedtime stories appropriate for ages 5 to 10."],
                error="request_out_of_scope",
            )
        )
        client = self.make_client(runner)

        response = client.post(
            "/",
            data={
                "request": "Write violent horror.",
                "model": "gpt-3.5-turbo",
            },
        )

        html = response.get_data(as_text=True)
        self.assertIn("request_out_of_scope", html)
        self.assertIn("appropriate for ages 5 to 10", html)

    def test_debug_panel_renders_only_when_requested(self):
        runner = FakeRunner(
            StoryResult(
                status=StoryStatus.PASSED,
                story="A cozy debug story.",
                final_judgment={"overall_score": 4.5},
                attempts_used=1,
                debug_info={"selected_model": "gpt-3.5-turbo"},
            )
        )
        client = self.make_client(runner)

        no_debug = client.post(
            "/",
            data={"request": "Tell me a story.", "model": "gpt-3.5-turbo"},
        )
        with_debug = client.post(
            "/",
            data={
                "request": "Tell me a story.",
                "model": "gpt-3.5-turbo",
                "debug": "on",
            },
        )

        self.assertNotIn("Debug details", no_debug.get_data(as_text=True))
        self.assertIn("Debug details", with_debug.get_data(as_text=True))
        self.assertTrue(runner.calls[-1]["debug"])


if __name__ == "__main__":
    unittest.main()

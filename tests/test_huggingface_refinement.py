import unittest

from engine import huggingface_refinement


class FakeResponse:
    status_code = 200
    text = ""

    def raise_for_status(self):
        return None

    def json(self):
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"decision":"NO_CHANGE"}',
                    }
                }
            ]
        }


class HuggingFaceRefinementTests(unittest.TestCase):
    def test_call_huggingface_chat_extracts_message_content(self):
        calls = []
        original_post = huggingface_refinement.requests.post

        def fake_post(*args, **kwargs):
            calls.append(
                {
                    "args": args,
                    "kwargs": kwargs,
                }
            )
            return FakeResponse()

        huggingface_refinement.requests.post = fake_post

        try:
            content = huggingface_refinement.call_huggingface_chat(
                "prompt",
                model="test/model",
                token="hf_test_token",
                base_url="https://example.test/v1/chat/completions",
            )
        finally:
            huggingface_refinement.requests.post = original_post

        self.assertEqual(content, '{"decision":"NO_CHANGE"}')
        self.assertEqual(
            calls[0]["kwargs"]["headers"]["Authorization"],
            "Bearer hf_test_token",
        )
        self.assertEqual(
            calls[0]["kwargs"]["json"]["model"],
            "test/model",
        )
        self.assertNotIn(
            "response_format",
            calls[0]["kwargs"]["json"],
        )

    def test_call_huggingface_chat_can_request_json_response(self):
        calls = []
        original_post = huggingface_refinement.requests.post

        def fake_post(*args, **kwargs):
            calls.append(
                {
                    "args": args,
                    "kwargs": kwargs,
                }
            )
            return FakeResponse()

        huggingface_refinement.requests.post = fake_post

        try:
            huggingface_refinement.call_huggingface_chat(
                "prompt",
                model="test/model",
                token="hf_test_token",
                request_json_response=True,
            )
        finally:
            huggingface_refinement.requests.post = original_post

        self.assertEqual(
            calls[0]["kwargs"]["json"]["response_format"],
            {
                "type": "json_object",
            },
        )

    def test_call_huggingface_chat_surfaces_error_body(self):
        class ErrorResponse:
            status_code = 400
            text = '{"error":"unsupported response_format"}'

            def json(self):
                return {}

        original_post = huggingface_refinement.requests.post

        def fake_post(*args, **kwargs):
            return ErrorResponse()

        huggingface_refinement.requests.post = fake_post

        try:
            with self.assertRaises(ValueError) as context:
                huggingface_refinement.call_huggingface_chat(
                    "prompt",
                    model="test/model",
                    token="hf_test_token",
                )
        finally:
            huggingface_refinement.requests.post = original_post

        self.assertIn("Hugging Face HTTP 400", str(context.exception))
        self.assertIn("unsupported response_format", str(context.exception))


if __name__ == "__main__":
    unittest.main()

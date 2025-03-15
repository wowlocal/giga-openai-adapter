import unittest
import yaml
from jsonschema import validate, ValidationError
from unittest.mock import MagicMock
from app.utils.giga_to_openai import SyncGigaToOpenai
from gigachat.models import ChatCompletion

# Remove the sys.path manipulation as it's not the recommended approach
# Instead, make sure the project root is in PYTHONPATH or use proper package installation

class TestSyncGigaToOpenaiSimple(unittest.TestCase):
    def setUp(self):
        self.converter = SyncGigaToOpenai()

        # Load the OpenAPI specification from file
        # and store it in a class variable for reuse
        try:
            with open("openapi.yaml", "r") as f:
                self.openapi_spec = yaml.safe_load(f)

            # Update the path to access the correct schema for chat completion response
            # The schema we need is for the message in the choices array, not the entire response
            self.chat_completion_schema = (
                self.openapi_spec
                .get("components", {})
                .get("schemas", {})
                .get("ChatCompletionResponseMessage", {})
            )
        except FileNotFoundError:
            print("Warning: openapi.yaml file not found. Schema validation will be skipped.")
            self.openapi_spec = {}
            self.chat_completion_schema = {}

    def test_convert_gigachat_to_openai_basic(self):
        """Test basic conversion from GigaChat to OpenAI format and validate via OpenAPI"""

        # Create a mock GigaChat completion
        mock_completion = MagicMock(spec=ChatCompletion)
        mock_completion.model = "GigaChat"
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message = MagicMock()
        mock_completion.choices[0].message.role = "assistant"
        mock_completion.choices[0].message.content = "This is a test response"

        # Convert to OpenAI format
        result = self.converter.convert_gigachat_to_openai(mock_completion)

        # Print the result for debugging
        print(f"Result type: {type(result)}")
        print(f"Result: {result}")

        # Basic sanity checks
        self.assertIsNotNone(result)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["role"], "assistant")
        self.assertEqual(result["content"], "This is a test response")
        self.assertEqual(result["model"], "GigaChat")

        # --- OpenAPI validation ---
        # Validate the `result` dict against the 'ChatCompletionResponseMessage' schema
        if not self.chat_completion_schema:
            self.fail("ChatCompletionResponseMessage schema not found in OpenAPI specification.")

        try:
            validate(instance=result, schema=self.chat_completion_schema)
        except ValidationError as e:
            self.fail(f"OpenAPI schema validation failed: {e}")

        # If no exception is raised, the test passes.


if __name__ == "__main__":
    unittest.main()

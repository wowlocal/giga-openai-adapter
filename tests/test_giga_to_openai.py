import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from unittest.mock import MagicMock, patch
from app.utils.giga_to_openai import SyncGigaToOpenai
from gigachat.models import Chat, Messages, MessagesRole, ChatCompletion
from typing import Dict, Any


class TestSyncGigaToOpenai(unittest.TestCase):
    def setUp(self):
        self.converter = SyncGigaToOpenai()

    def test_convert_gigachat_to_openai_basic(self):
        """Test basic conversion from GigaChat to OpenAI format"""
        # Create a mock GigaChat completion
        mock_completion = MagicMock(spec=ChatCompletion)
        mock_completion.model = "GigaChat"
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message = MagicMock()
        mock_completion.choices[0].message.role = "assistant"
        mock_completion.choices[0].message.content = "This is a test response"

        # Convert to OpenAI format
        result = self.converter.convert_gigachat_to_openai(mock_completion)

        # Verify the conversion
        self.assertIsInstance(result, dict)
        self.assertEqual(result["role"], "assistant")
        self.assertEqual(result["content"], "This is a test response")
        self.assertEqual(result["model"], "GigaChat")

    def test_convert_gigachat_to_openai_with_different_role(self):
        """Test conversion with a different role"""
        # Create a mock GigaChat completion with user role
        mock_completion = MagicMock(spec=ChatCompletion)
        mock_completion.model = "GigaChat-Pro"
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message = MagicMock()
        mock_completion.choices[0].message.role = "user"
        mock_completion.choices[0].message.content = "User message content"

        # Convert to OpenAI format
        result = self.converter.convert_gigachat_to_openai(mock_completion)

        # Verify the conversion
        self.assertEqual(result["role"], "user")
        self.assertEqual(result["content"], "User message content")
        self.assertEqual(result["model"], "GigaChat-Pro")

    def test_convert_gigachat_to_openai_with_empty_content(self):
        """Test conversion with empty content"""
        # Create a mock GigaChat completion with empty content
        mock_completion = MagicMock(spec=ChatCompletion)
        mock_completion.model = "GigaChat"
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message = MagicMock()
        mock_completion.choices[0].message.role = "assistant"
        mock_completion.choices[0].message.content = ""

        # Convert to OpenAI format
        result = self.converter.convert_gigachat_to_openai(mock_completion)

        # Verify the conversion
        self.assertEqual(result["content"], "")

    def test_dictionary_structure(self):
        """Test that the conversion returns a dictionary with the correct structure"""
        # Create a mock GigaChat completion
        mock_completion = MagicMock(spec=ChatCompletion)
        mock_completion.model = "GigaChat"
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message = MagicMock()
        mock_completion.choices[0].message.role = "assistant"
        mock_completion.choices[0].message.content = "Test content"

        # Call the conversion method
        result = self.converter.convert_gigachat_to_openai(mock_completion)

        # Verify the dictionary structure
        self.assertIsInstance(result, dict)
        self.assertIn("role", result)
        self.assertIn("content", result)
        self.assertIn("model", result)
        self.assertEqual(result["role"], mock_completion.choices[0].message.role)
        self.assertEqual(result["content"], mock_completion.choices[0].message.content)
        self.assertEqual(result["model"], mock_completion.model)

    def test_with_actual_gigachat_models(self):
        """Test conversion using actual GigaChat model classes instead of mocks"""
        # Create a message for the ChatCompletion
        message = MagicMock()
        message.role = "assistant"
        message.content = "This is a response from the actual GigaChat model"

        # Create a choice for the ChatCompletion
        choice = MagicMock()
        choice.index = 0
        choice.message = message
        choice.finish_reason = "stop"

        # Create a ChatCompletion object
        completion = MagicMock(spec=ChatCompletion)
        completion.id = "chat-123456"
        completion.object = "chat.completion"
        completion.created = 1615221580
        completion.model = "GigaChat-Pro"
        completion.choices = [choice]
        completion.usage = {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}

        # Convert to OpenAI format
        result = self.converter.convert_gigachat_to_openai(completion)

        # Verify the conversion
        self.assertIsInstance(result, dict)
        self.assertEqual(result["role"], "assistant")
        self.assertEqual(result["content"], "This is a response from the actual GigaChat model")
        self.assertEqual(result["model"], "GigaChat-Pro")


if __name__ == "__main__":
    unittest.main()
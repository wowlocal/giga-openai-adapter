# import openai models
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
# import gigachat models
from gigachat import GigaChat
from gigachat.models import Messages, MessagesRole, Function, FunctionParameters, ChatCompletion
from typing import Dict, Any


class SyncGigaToOpenai:
    def convert_gigachat_to_openai(self, completion: ChatCompletion) -> Dict[str, Any]:
        """
        Convert a GigaChat message to an OpenAI chat completion message.
		"""
        # Create a dictionary that matches the structure of ChatCompletionMessageParam
        openai_message = {
            "role": completion.choices[0].message.role,
            "content": completion.choices[0].message.content,
            "model": completion.model,
            "refusal": None  # Adding the required 'refusal' field with null value
        }
        return openai_message


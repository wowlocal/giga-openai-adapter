from gigachat import GigaChat
import certifi
import ssl
import os
import asyncio
import json
from dotenv import load_dotenv

from gigachat.models import Chat, Function, FunctionParameters, Messages, MessagesRole, FunctionCall

# Get the current directory
current_dir = os.path.dirname(os.path.abspath(__file__))

# Load environment variables
load_dotenv()

# Path to your additional trusted certificate (.cer file)
custom_cert_path = os.path.join(current_dir, "russian_trusted_root_ca.cer")

# Define a search function for function calling
search_fn = Function(
    name="duckduckgo_search",
    description="""Поиск в DuckDuckGo.
Полезен, когда нужно ответить на вопросы о текущих событиях.
Входными данными должен быть поисковый запрос.""",
    parameters=FunctionParameters(
        type="object",
        properties={"query": {"type": "string", "description": "Поисковый запрос"}},
        required=["query"],
    ),
)

search = search_fn

# Define a calculator function
calculator_fn = Function(
    name="calculator",
    description="Выполняет математические вычисления",
    parameters=FunctionParameters(
        type="object",
        properties={
            "expression": {"type": "string", "description": "Математическое выражение для вычисления"}
        },
        required=["expression"],
    ),
)

async def test_chat_completion():
    """Test basic chat completion"""
    key = os.getenv("MASTER_TOKEN")

    print("\n=== Testing Basic Chat Completion ===")
    async with GigaChat(
        credentials=key,
        verify_ssl_certs=False,  # Disable SSL verification for testing
        ca_bundle_file=custom_cert_path if os.path.exists(custom_cert_path) else None
    ) as giga:
        chat = Chat(
            messages=[
                Messages(
                    role=MessagesRole.SYSTEM,
                    content="Ты - умный ИИ ассистент, который всегда готов помочь пользователю.",
                ),
                Messages(
                    role=MessagesRole.USER,
                    content="Расскажи о себе кратко",
                ),
            ]
        )

        try:
            response = await giga.achat(chat)
            print(f"Model: {response.model}")
            print(f"Response: {response.choices[0].message.content}")
            print(f"Usage: {response.usage.total_tokens} tokens")
        except Exception as e:
            print(f"Error in chat completion: {str(e)}")

async def test_streaming():
    """Test streaming chat completion"""
    key = os.getenv("MASTER_TOKEN")

    print("\n=== Testing Streaming Chat Completion ===")
    async with GigaChat(
        credentials=key,
        verify_ssl_certs=False,
        ca_bundle_file=custom_cert_path if os.path.exists(custom_cert_path) else None
    ) as giga:
        chat = Chat(
            messages=[
                Messages(
                    role=MessagesRole.SYSTEM,
                    content="Ты - умный ИИ ассистент, который всегда готов помочь пользователю.",
                ),
                Messages(
                    role=MessagesRole.USER,
                    content="Напиши короткое стихотворение о программировании",
                ),
            ],
            update_interval=0.1  # For streaming
        )

        print("Streaming response:")
        try:
            async for chunk in giga.astream(chat):
                if hasattr(chunk, 'choices') and chunk.choices:
                    for choice in chunk.choices:
                        if hasattr(choice, 'delta') and choice.delta:
                            if hasattr(choice.delta, 'content') and choice.delta.content:
                                print(choice.delta.content, end="", flush=True)
            print("\n")
        except Exception as e:
            print(f"Error in streaming: {str(e)}")

async def test_function_calling():
    """Test function calling"""
    key = os.getenv("MASTER_TOKEN")

    print("\n=== Testing Function Calling ===")
    async with GigaChat(
        credentials=key,
        verify_ssl_certs=False,
        ca_bundle_file=custom_cert_path if os.path.exists(custom_cert_path) else None
    ) as giga:
        chat = Chat(
            messages=[
                Messages(
                    role=MessagesRole.SYSTEM,
                    content="Ты - умный ИИ ассистент, который всегда готов помочь пользователю.",
                ),
                Messages(
                    role=MessagesRole.USER,
                    content="Найди информацию о последних технологических новостях",
                ),
            ],
            functions=[search_fn],
        )

        try:
            response = await giga.achat(chat)

            # Check if function call is present
            if hasattr(response.choices[0].message, 'function_call'):
                function_call = response.choices[0].message.function_call
                print(f"Function called: {function_call.name}")
                print(f"Arguments: {function_call.arguments}")

                # Simulate function execution
                search_results = "Найдены последние технологические новости: выпущен новый iPhone, Tesla представила новую модель, Microsoft анонсировала Windows 12."

                # Continue the conversation with function results
                chat.messages.append(Messages(
                    role=MessagesRole.ASSISTANT,
                    content=None,
                    function_call=FunctionCall(
                        name=function_call.name,
                        arguments=function_call.arguments
                    )
                ))

                chat.messages.append(Messages(
                    role=MessagesRole.FUNCTION,
                    name=function_call.name,
                    content=search_results
                ))

                chat.messages.append(Messages(
                    role=MessagesRole.USER,
                    content="Расскажи подробнее о новом iPhone"
                ))

                # Get the final response
                final_response = await giga.achat(chat)
                print(f"\nFinal response: {final_response.choices[0].message.content}")
            else:
                print(f"No function call, direct response: {response.choices[0].message.content}")
        except Exception as e:
            print(f"Error in function calling: {str(e)}")

async def test_multiple_functions():
    """Test with multiple functions"""
    key = os.getenv("MASTER_TOKEN")

    print("\n=== Testing Multiple Functions ===")
    async with GigaChat(
        credentials=key,
        verify_ssl_certs=False,
        ca_bundle_file=custom_cert_path if os.path.exists(custom_cert_path) else None
    ) as giga:
        messages = []
        function_called = False
        while True:
            # Если предыдущий ответ LLM не был вызовом функции - просим пользователя продолжить диалог
            if not function_called:
                query = input("\033[92mUser: \033[0m")
                messages.append(Messages(role=MessagesRole.USER, content=query))

            chat = Chat(messages=messages, functions=[search])

            resp = giga.chat(chat).choices[0]
            mess = resp.message
            messages.append(mess)

            print("\033[93m" + f"Bot: \033[0m{mess.content}")

            function_called = False
            func_result = ""
            if resp.finish_reason == "function_call":
                print("\033[90m" + f"  >> Processing function call {mess.function_call}" + "\033[0m")
                if mess.function_call.name == "duckduckgo_search":
                    query = mess.function_call.arguments.get("query", None)
                    if query:
                        func_result = search_ddg(query)
                print("\033[90m" + f"  << Function result: {func_result}\n\n" + "\033[0m")

                messages.append(
                    Messages(role=MessagesRole.FUNCTION,
                            content=json.dumps({"result": func_result}, ensure_ascii=False))
                )
                function_called = True

async def test_embeddings():
    """Test embeddings functionality"""
    key = os.getenv("MASTER_TOKEN")

    print("\n=== Testing Embeddings ===")
    async with GigaChat(
        credentials=key,
        verify_ssl_certs=False,
        ca_bundle_file=custom_cert_path if os.path.exists(custom_cert_path) else None
    ) as giga:
        texts = [
            "Привет, мир!",
            "Искусственный интеллект - это будущее",
            "Машинное обучение - подраздел искусственного интеллекта"
        ]

        try:
            response = await giga.aembeddings(texts)
            print(f"Generated {len(response.data)} embeddings")
            print(f"Embedding dimensions: {len(response.data[0].embedding)}")

            # Calculate similarity between first and second embedding
            import numpy as np
            embedding1 = np.array(response.data[0].embedding)
            embedding2 = np.array(response.data[1].embedding)
            similarity = np.dot(embedding1, embedding2) / (np.linalg.norm(embedding1) * np.linalg.norm(embedding2))
            print(f"Similarity between first and second text: {similarity}")
        except Exception as e:
            print(f"Error in embeddings: {str(e)}")

async def main():
    """Run all tests"""
    try:
        # Test basic chat completion
        await test_chat_completion()

        # Test streaming
        await test_streaming()

        # Test function calling
        await test_function_calling()

        # Test multiple functions
        await test_multiple_functions()

        # Test embeddings
        await test_embeddings()
    except Exception as e:
        print(f"Error in main: {str(e)}")

# Run the async function
if __name__ == "__main__":
    asyncio.run(main())
from gigachat import GigaChat
import certifi
import ssl
import os
from dotenv import load_dotenv

from gigachat.models import Chat, Function, FunctionParameters, Messages, MessagesRole, FunctionCall

current_dir = os.path.dirname(os.path.abspath(__file__))

# load env variables
load_dotenv()

# Path to your additional trusted certificate (.cer file)
custom_cert_path = os.path.join(current_dir, "russian_trusted_root_ca.cer")

# Укажите ключ авторизации, полученный в личном кабинете, в интерфейсе проекта GigaChat API
import asyncio

PAYLOAD = Chat(
    messages=[
        Messages(
            role=MessagesRole.SYSTEM,
            content="Ты - умный ИИ ассистент, который всегда готов помочь пользователю.",
        ),
        Messages(
            role=MessagesRole.ASSISTANT,
            content="Как я могу помочь вам?",
        ),
        Messages(
            role=MessagesRole.USER,
            content="Напиши подробный доклад на тему жизни Пушкина в Москве",
        ),
    ],
    update_interval=0.1,
)

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

async def main():
    key = os.getenv("MASTER_TOKEN")
    async with GigaChat(
        credentials=key,
        verify_ssl_certs=False
    ) as giga:
        print(giga.get_models())
        response = giga.embeddings(["Hello world!"])
        # print(response)

    async with GigaChat(
        credentials=key,
        verify_ssl_certs=False  # Disable SSL verification
    ) as giga:
        payload = "Найди что-нибудь интересное в интернете"
        chat = Chat(
            messages=[
                Messages(
                    role=MessagesRole.USER,
                    content=payload,
                ),
            ],
            functions=[search_fn],
        )
        async for chunk in giga.astream(chat):
            if hasattr(chunk, 'choices') and chunk.choices:
                for choice in chunk.choices:
                    if choice.delta and choice.delta.content:
                        print(choice.delta.content, end="", flush=True)

# Run the async function
if __name__ == "__main__":
    asyncio.run(main())
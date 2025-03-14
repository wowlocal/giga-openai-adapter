from openai import OpenAI
import ssl
import certifi
import httpx

# Create custom SSL context that allows self-signed certificates
ssl_context = httpx.create_ssl_context(verify=False)
http_client = httpx.Client(verify=False)

token = "<TOKEN>"

client = OpenAI(api_key=token,
                base_url="https://gigachat.devices.sberbank.ru/api/v1",
                http_client=http_client
                )
completion = client.chat.completions.create(
    model="GigaChat",
    messages=[
        {"role": "system", "content": "Как приготовить борщ?"},
        {
            "role": "user",
            "content": "yoooo!"
        }
    ]
)
print(completion.choices[0].message)
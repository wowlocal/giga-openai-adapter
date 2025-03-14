from gigachat import GigaChat
import certifi
import ssl
import os
from dotenv import load_dotenv
current_dir = os.path.dirname(os.path.abspath(__file__))

# load env variables
load_dotenv()

key = os.getenv("MASTER_TOKEN")

# Path to your additional trusted certificate (.cer file)
custom_cert_path = os.path.join(current_dir, "russian_trusted_root_ca.cer")

# Укажите ключ авторизации, полученный в личном кабинете, в интерфейсе проекта GigaChat API
with GigaChat(
    credentials=key,
    verify_ssl_certs=False  # Disable SSL verification
) as giga:
    response = giga.chat("Какие факторы влияют на стоимость страховки на дом?")
    print(response.choices[0].message.content)
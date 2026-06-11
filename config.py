import os
from dotenv import load_dotenv

# Carga las variables del archivo .env
load_dotenv()

# Lee las variables de entorno
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

# Verifica que existan las variables necesarias
if not WHATSAPP_TOKEN:
    raise ValueError("❌ Falta la variable WHATSAPP_TOKEN en el archivo .env")

if not PHONE_NUMBER_ID:
    raise ValueError("❌ Falta la variable PHONE_NUMBER_ID en el archivo .env. "
                     "La necesitas para poder enviar mensajes.")

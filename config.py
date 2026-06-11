import os
from dotenv import load_dotenv

# Carga las variables del archivo .env (si existe)
load_dotenv()

# Lee las variables de entorno (del .env o del sistema)
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
WEBHOOK_VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN", "mi_token_secreto_123")

# Solo advertimos si faltan, no fallamos (para que el servidor arranque igual)
if not WHATSAPP_TOKEN:
    print("⚠️  ADVERTENCIA: Falta la variable WHATSAPP_TOKEN. El envío de mensajes no funcionará.")

if not PHONE_NUMBER_ID:
    print("⚠️  ADVERTENCIA: Falta la variable PHONE_NUMBER_ID. El envío de mensajes no funcionará.")

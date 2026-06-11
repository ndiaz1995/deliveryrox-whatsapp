# 🤖 DeliveryRox - Centro de Mando WhatsApp

Sistema de automatización para WhatsApp Business usando la API oficial de Meta.

## ✨ Features

- 📨 **Recepción de mensajes** vía webhooks de Meta
- 💬 **Dashboard web** para ver y responder conversaciones
- 🗄️ **Base de datos SQLite** para almacenar contactos y mensajes
- 📊 **Estadísticas en tiempo real**
- 🤖 **Escucha activa** 24/7

## 🚀 Deploy en Render.com

### 1. Variables de entorno necesarias

Crea un archivo `.env` local (no se sube a GitHub):

```env
WHATSAPP_TOKEN=tu_token_de_meta
PHONE_NUMBER_ID=tu_phone_number_id
WEBHOOK_VERIFY_TOKEN=mi_token_secreto_123
```

### 2. Instalación local

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

### 3. Webhook en Meta

- **Callback URL**: `https://tu-app.onrender.com/webhook`
- **Verify Token**: `mi_token_secreto_123`

## 📁 Estructura

```
├── app.py              # Servidor Flask
├── database.py         # SQLite
├── whatsapp_client.py  # API de Meta
├── config.py           # Configuración
├── templates/          # Dashboard HTML
├── static/             # CSS
└── requirements.txt    # Dependencias
```

## 📝 Notas

- El token de Meta expira cada 24 horas (genera uno nuevo en el panel de Meta)
- Para producción, crea un token permanente en Meta Business Manager

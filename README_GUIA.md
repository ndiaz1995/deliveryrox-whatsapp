# 🚀 Guía para Conectar con WhatsApp Business API de Meta

## 📁 Estructura del Proyecto

```
├── .env                     # Tus secretos (token, IDs)
├── venv/                    # Entorno virtual
├── config.py                # Lee las variables de entorno
├── whatsapp_client.py       # Cliente para la API de Meta
├── send_test.py             # Script para enviar mensajes de prueba
├── webhook_receiver.py      # Servidor para recibir mensajes
└── README_GUIA.md           # Esta guía
```

---

## 🔧 Paso 1: Configurar tu archivo .env

Tu archivo `.env` debe tener estas variables:

```env
# El token que ya te dio Meta (si se llama diferente, renómbralo así)
WHATSAPP_TOKEN=tu_token_aqui

# El ID de tu número de teléfono en Meta (ver cómo obtener abajo)
PHONE_NUMBER_ID=12345678901234
```

---

## 🔑 Paso 2: ¿Cómo obtener el PHONE_NUMBER_ID?

El token ya lo tienes, pero para **enviar** mensajes también necesitas el `PHONE_NUMBER_ID`.

### Opción A: Desde el panel de Meta (más fácil)
1. Ve a: https://business.facebook.com/wa/manage/phone-numbers/
2. Selecciona tu número de teléfono
3. El `PHONE_NUMBER_ID` aparece en la URL o en la información del número
4. Copia ese número y ponlo en tu `.env`

### Opción B: Desde Meta for Developers
1. Ve a: https://developers.facebook.com/apps/
2. Entra a tu app de WhatsApp
3. En el panel izquierdo ve a **WhatsApp > Getting Started**
4. Ahí verás:
   - **Phone number ID**: algo como `12345678901234`
   - **WhatsApp Business Account ID**: otro ID (lo usamos después)

---

## ▶️ Paso 3: Probar el envío de mensajes

### Activar el entorno virtual:

**En Windows (Git Bash):**
```bash
source venv/Scripts/activate
```

**En Windows (CMD):**
```cmd
venv\Scripts\activate.bat
```

**En Mac/Linux:**
```bash
source venv/bin/activate
```

### Enviar un mensaje de prueba:
```bash
python send_test.py
```

Te pedirá:
1. El número al que quieres escribir (formato internacional sin `+`, ej: `5215512345678`)
2. El mensaje que quieres enviar

> ⚠️ **Importante**: Meta solo te deja enviar mensajes a números que te hayan escrito primero, o que hayan interactuado con tu número en las últimas 24 horas (ventana de conversación). Si el número nunca te ha escrito, tendrás que usar un **template** (plantilla) aprobado por Meta.

---

## 📥 Paso 4: Recibir mensajes (Webhooks)

Para recibir mensajes cuando alguien te escriba, necesitas:

### 1. Correr el servidor local:
```bash
python webhook_receiver.py
```

### 2. Exponerlo a internet con ngrok:

Descarga ngrok de https://ngrok.com/download (o con `choco install ngrok` en Windows)

```bash
ngrok http 8000
```

Te dará una URL como: `https://abc123.ngrok-free.app`

### 3. Configurar el webhook en Meta:
1. Ve a tu app en https://developers.facebook.com/apps/
2. Ve a **WhatsApp > Configuration**
3. En **Webhook** haz clic en **Edit**
4. **Callback URL**: `https://abc123.ngrok-free.app` (tu URL de ngrok)
5. **Verify token**: `mi_token_secreto_123` (está en `webhook_receiver.py`)
6. Haz clic en **Verify and Save**
7. Después suscríbete al campo **messages** haciendo clic en **Add Subscriptions**

¡Listo! Cuando alguien te escriba, verás el mensaje en la terminal.

---

## 📝 Notas Importantes sobre Meta

### ¿Por qué no puedo escribir a cualquier número?
Meta tiene reglas estrictas:
- **Conversaciones iniciadas por el usuario**: Si alguien te escribe primero, puedes responder libremente por 24 horas.
- **Conversaciones iniciadas por la empresa (tú)**: Solo puedes enviar **templates** (plantillas) pre-aprobadas por Meta. No puedes enviar texto libre.

### ¿Cómo crear un template (plantilla)?
1. Ve a https://business.facebook.com/wa/manage/templates/
2. Crea una nueva plantilla (ej: "Hola, gracias por contactarnos")
3. Meta la revisa (toma unas horas o días)
4. Una vez aprobada, puedes enviarla a cualquier número

### Tipos de mensajes que puedes enviar:
- `text` - Texto simple
- `image` - Imagen (con URL pública)
- `document` - PDF, etc.
- `template` - Plantillas aprobadas

---

## 🆘 Solución de Problemas

### "Error 400: Invalid token"
- Tu token expiró. Ve a Meta y genera uno nuevo.

### "Error 400: Invalid phone number"
- Verifica el formato. Debe ser internacional sin espacios ni `+`. Ejemplo México: `5215512345678`

### "Error 400: Message failed to send"
- Probablemente intentaste escribir a un número que nunca te escribió. Usa un template.

### "No me llegan los webhooks"
- Verifica que ngrok esté corriendo
- Verifica que la URL en Meta sea exactamente la de ngrok
- Verifica que el verify token sea exactamente `mi_token_secreto_123`

---

## 🎯 Próximos Pasos

Cuando quieras avanzar más, podemos agregar:
- 📎 Envío de imágenes y documentos
- 📋 Uso de templates aprobados
- 🤖 Respuestas automáticas con IA
- 📊 Guardar mensajes en base de datos

¡Dime qué quieres probar! 🚀

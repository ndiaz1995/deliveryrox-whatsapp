import json
import os
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

from database import (
    init_db, save_message, get_messages, get_conversations,
    get_stats, mark_conversation_as_read, get_contact
)
from whatsapp_client import WhatsAppClient

# Carga variables de entorno
load_dotenv()

app = Flask(__name__)

# Token de verificación para los webhooks de Meta
VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN", "mi_token_secreto_123")

# Inicializa la base de datos al arrancar
init_db()


# ============================================================
# RUTA PRINCIPAL - CENTRO DE MANDO (DASHBOARD)
# ============================================================
@app.route("/")
def dashboard():
    """Muestra el centro de mando con todas las conversaciones."""
    conversations = get_conversations()
    stats = get_stats()
    return render_template("index.html", conversations=conversations, stats=stats)


# ============================================================
# API - ENDPOINTS JSON PARA EL DASHBOARD
# ============================================================
@app.route("/api/stats")
def api_stats():
    """Retorna estadísticas en JSON."""
    return jsonify(get_stats())


@app.route("/api/conversations")
def api_conversations():
    """Retorna todas las conversaciones en JSON."""
    return jsonify(get_conversations())


@app.route("/api/messages/<phone_number>")
def api_messages(phone_number):
    """Retorna los mensajes de un número específico."""
    messages = get_messages(phone_number)
    contact = get_contact(phone_number)
    return jsonify({
        "contact": contact,
        "messages": messages
    })


@app.route("/api/send", methods=["POST"])
def api_send():
    """Envía un mensaje desde el dashboard."""
    data = request.json
    phone_number = data.get("phone_number", "").strip()
    message = data.get("message", "").strip()

    if not phone_number or not message:
        return jsonify({"error": "Número y mensaje son requeridos"}), 400

    try:
        client = WhatsAppClient()
        result = client.send_text_message(phone_number, message)

        # Guarda el mensaje enviado en la base de datos
        save_message(
            phone_number=phone_number,
            content=message,
            message_type="text",
            direction="outgoing"
        )

        return jsonify({"success": True, "result": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/read/<phone_number>", methods=["POST"])
def api_read(phone_number):
    """Marca una conversación como leída."""
    mark_conversation_as_read(phone_number)
    return jsonify({"success": True})


# ============================================================
# WEBHOOK - RECIBIR MENSAJES DE META
# ============================================================
@app.route("/webhook", methods=["GET"])
def webhook_verify():
    """
    Meta envía una petición GET para verificar que este servidor es tuyo.
    Debes configurar esta URL en Meta con el VERIFY_TOKEN.
    """
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print(f"✅ Webhook verificado correctamente!")
        return challenge, 200
    else:
        print(f"❌ Falló la verificación del webhook")
        return "Forbidden", 403


@app.route("/webhook", methods=["POST"])
def webhook_receive():
    """
    Recibe los eventos de WhatsApp (mensajes entrantes, etc.)
    Meta enviará un JSON cada vez que alguien te escriba.
    """
    try:
        data = request.json
        print("\n" + "=" * 60)
        print(f"📩 [{datetime.now().strftime('%H:%M:%S')}] Webhook recibido")

        # Procesar cada entrada
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})

                # Solo procesamos mensajes
                if "messages" not in value:
                    continue

                for msg in value["messages"]:
                    phone_number = msg.get("from")
                    msg_id = msg.get("id")
                    msg_type = msg.get("type")
                    timestamp = msg.get("timestamp")

                    # Convertir timestamp de Unix a ISO
                    if timestamp:
                        timestamp = datetime.fromtimestamp(int(timestamp)).isoformat()
                    else:
                        timestamp = datetime.now().isoformat()

                    # Obtener nombre del perfil si existe
                    contacts = value.get("contacts", [])
                    profile_name = contacts[0].get("profile", {}).get("name") if contacts else None

                    # Extraer contenido según el tipo
                    content = ""
                    if msg_type == "text":
                        content = msg.get("text", {}).get("body", "")
                    elif msg_type == "image":
                        content = "[Imagen recibida]"
                    elif msg_type == "document":
                        content = "[Documento recibido]"
                    elif msg_type == "audio":
                        content = "[Audio recibido]"
                    elif msg_type == "video":
                        content = "[Video recibido]"
                    elif msg_type == "location":
                        loc = msg.get("location", {})
                        content = f"[Ubicación: {loc.get('latitude')}, {loc.get('longitude')}]"
                    else:
                        content = f"[{msg_type.upper()} recibido]"

                    # Guardar en base de datos
                    is_new = save_message(
                        phone_number=phone_number,
                        content=content,
                        message_id=msg_id,
                        message_type=msg_type,
                        timestamp=timestamp,
                        direction="incoming",
                        profile_name=profile_name
                    )

                    if is_new:
                        display_name = profile_name or phone_number
                        print(f"💬 [{display_name}] {content}")
                        print(f"   📱 Número: {phone_number}")
                        print(f"   🆔 ID: {msg_id}")
                    else:
                        print(f"⏩ Mensaje duplicado ignorado: {msg_id}")

        print("=" * 60)
        return "OK", 200

    except Exception as e:
        print(f"❌ Error procesando webhook: {e}")
        return "OK", 200  # Siempre respondemos 200 a Meta


# ============================================================
# INICIAR SERVIDOR
# ============================================================
if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║         🤖 DELIVERYROX - CENTRO DE MANDO WHATSAPP        ║
    ╠═══════════════════════════════════════════════════════════╣
    ║  🌐 Dashboard:  http://localhost:5000                     ║
    ║  🔗 Webhook:    http://localhost:5000/webhook             ║
    ║  🔑 Verify Token: {}                 ║
    ╠═══════════════════════════════════════════════════════════╣
    ║  Para exponer a internet (Meta requiere esto):           ║
    ║  → ngrok http 5000                                       ║
    ╚═══════════════════════════════════════════════════════════╝
    """.format(VERIFY_TOKEN))

    app.run(host="0.0.0.0", port=5000, debug=True)

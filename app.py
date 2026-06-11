import json
import os
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

from database import (
    init_db, save_message, get_messages, get_conversations,
    get_stats, mark_conversation_as_read, get_contact,
    get_conversation_state, update_conversation_state,
    get_orders_by_phone
)
from chatbot import DMARBot
from database import get_bot_config, save_bot_config
from workflow_engine import serialize_workflow, deserialize_workflow, validate_workflow

# Carga variables de entorno
load_dotenv()

app = Flask(__name__)

# Token de verificación para los webhooks de Meta
VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN", "mi_token_secreto_123")

# Inicializa base de datos y bot
init_db()
bot = DMARBot()


# ============================================================
# RUTA PRINCIPAL - CENTRO DE MANDO
# ============================================================
@app.route("/")
def dashboard():
    """Muestra el centro de mando con todas las conversaciones."""
    conversations = get_conversations()
    stats = get_stats()
    return render_template("index.html", conversations=conversations, stats=stats)


# ============================================================
# API - ENDPOINTS JSON
# ============================================================
@app.route("/api/stats")
def api_stats():
    return jsonify(get_stats())


@app.route("/api/conversations")
def api_conversations():
    return jsonify(get_conversations())


@app.route("/api/messages/<phone_number>")
def api_messages(phone_number):
    messages = get_messages(phone_number)
    contact = get_contact(phone_number)
    state = get_conversation_state(phone_number)
    orders = get_orders_by_phone(phone_number)
    return jsonify({
        "contact": contact,
        "state": state,
        "orders": orders,
        "messages": messages
    })


@app.route("/api/send", methods=["POST"])
def api_send():
    """Envía un mensaje desde el dashboard (humano)."""
    data = request.json
    phone_number = data.get("phone_number", "").strip()
    message = data.get("message", "").strip()

    if not phone_number or not message:
        return jsonify({"error": "Número y mensaje son requeridos"}), 400

    # Guardar mensaje saliente en DB
    save_message(
        phone_number=phone_number,
        content=message,
        direction="outgoing"
    )

    # Si tiene token de Meta, enviar por WhatsApp real
    if os.getenv("WHATSAPP_TOKEN") and os.getenv("PHONE_NUMBER_ID"):
        try:
            from whatsapp_client import WhatsAppClient
            client = WhatsAppClient()
            result = client.send_text_message(phone_number, message)
            return jsonify({"success": True, "result": result})
        except Exception as e:
            return jsonify({"success": False, "sent_locally": True, "error": str(e)})
    else:
        return jsonify({"success": True, "sent_locally": True, "note": "Modo sin token de Meta"})


@app.route("/api/read/<phone_number>", methods=["POST"])
def api_read(phone_number):
    mark_conversation_as_read(phone_number)
    return jsonify({"success": True})


@app.route("/api/handoff/<phone_number>", methods=["POST"])
def api_handoff(phone_number):
    """Activa/desactiva atención humana."""
    data = request.json or {}
    active = data.get("active", True)
    state = get_conversation_state(phone_number)
    current_node = state.get('current_node') or bot.start_node
    update_conversation_state(
        phone_number, current_node, {}, human_handoff=1 if active else 0
    )
    return jsonify({"success": True, "human_handoff": active})


@app.route("/api/reset/<phone_number>", methods=["POST"])
def api_reset(phone_number):
    """Reinicia el estado del bot para un número."""
    bot.reset_state(phone_number)
    return jsonify({"success": True})


@app.route("/api/config", methods=["GET"])
def api_get_config():
    """Obtiene la configuración actual del bot (visual + ejecutable)."""
    config = get_bot_config()
    return jsonify(config)


@app.route("/api/config", methods=["POST"])
def api_save_config():
    """
    Guarda la configuración del bot.
    Recibe formato visual {nodes, connections}, lo serializa a ejecutable,
    valida y guarda ambos formatos.
    """
    data = request.json or {}
    
    # Puede recibir formato visual o ejecutable directo
    visual = data.get("visual")
    executable = data.get("executable")
    
    if visual:
        # Serializar visual → ejecutable
        nodes = visual.get("nodes", [])
        connections = visual.get("connections", [])
        executable = serialize_workflow(nodes, connections)
    
    if not executable:
        return jsonify({"error": "Se requiere 'visual' o 'executable'"}), 400
    
    # Validar
    is_valid, error_msg = validate_workflow(executable)
    if not is_valid:
        return jsonify({"error": error_msg}), 400
    
    # Guardar
    save_bot_config(visual=visual, executable=executable)
    bot.reload()  # Recargar en memoria
    return jsonify({"success": True, "start_node": executable.get("start_node")})


@app.route("/api/health")
def api_health():
    """Diagnóstico del sistema."""
    token = os.getenv("WHATSAPP_TOKEN")
    phone_id = os.getenv("PHONE_NUMBER_ID")
    verify = os.getenv("WEBHOOK_VERIFY_TOKEN")
    
    # Verificar si token tiene formato válido (no vacío y largo razonable)
    token_ok = bool(token and len(token) > 20)
    phone_ok = bool(phone_id and len(phone_id) > 5)
    
    return jsonify({
        "status": "ok" if (token_ok and phone_ok) else "missing_config",
        "whatsapp_token_configured": token_ok,
        "phone_number_id_configured": phone_ok,
        "webhook_verify_token_configured": bool(verify),
        "token_length": len(token) if token else 0,
        "phone_id": phone_id if phone_ok else None,
    })


# ============================================================
# ENDPOINT DE PRUEBA DIRECTA (para diagnosticar envíos)
# ============================================================
@app.route("/api/send-test", methods=["GET", "POST"])
def api_send_test():
    """
    Endpoint simple para probar envíos directamente.
    GET: /api/send-test?phone=584120521377&message=Hola
    POST: JSON con phone y message
    """
    if request.method == "GET":
        phone_number = request.args.get("phone", "").strip()
        message = request.args.get("message", "").strip()
    else:
        data = request.json or {}
        phone_number = data.get("phone", "").strip()
        message = data.get("message", "").strip()
    
    if not phone_number or not message:
        return jsonify({"error": "Faltan parametros phone y message"}), 400
    
    token = os.getenv("WHATSAPP_TOKEN")
    phone_id = os.getenv("PHONE_NUMBER_ID")
    
    print(f"\n🧪 TEST ENVIO:")
    print(f"   📱 Destino: {phone_number}")
    print(f"   💬 Mensaje: {message}")
    print(f"   🔑 Token configurado: {bool(token)} (length: {len(token) if token else 0})")
    print(f"   📞 Phone ID: {phone_id}")
    
    if not token or not phone_id:
        return jsonify({
            "error": "Falta configuracion",
            "token_configured": bool(token),
            "phone_id_configured": bool(phone_id)
        }), 500
    
    try:
        from whatsapp_client import WhatsAppClient
        client = WhatsAppClient()
        result = client.send_text_message(phone_number, message)
        print(f"   ✅ ENVIADO EXITOSAMENTE")
        return jsonify({"success": True, "result": result})
    except Exception as e:
        print(f"   ❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# WEBHOOK - RECIBIR MENSAJES DE META
# ============================================================
@app.route("/webhook", methods=["GET"])
def webhook_verify():
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
    """Recibe eventos de WhatsApp y procesa con el bot automático."""
    try:
        data = request.json
        print("\n" + "=" * 60)
        print(f"📩 [{datetime.now().strftime('%H:%M:%S')}] Webhook recibido")

        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})

                if "messages" not in value:
                    continue

                for msg in value["messages"]:
                    phone_number = msg.get("from")
                    msg_id = msg.get("id")
                    msg_type = msg.get("type")
                    timestamp = msg.get("timestamp")

                    if timestamp:
                        timestamp = datetime.fromtimestamp(int(timestamp)).isoformat()
                    else:
                        timestamp = datetime.now().isoformat()

                    contacts = value.get("contacts", [])
                    profile_name = contacts[0].get("profile", {}).get("name") if contacts else None

                    # Extraer contenido
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

                    # Guardar mensaje en DB
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

                        # ===== BOT AUTOMÁTICO =====
                        bot_response = bot.process_message(phone_number, content, profile_name)

                        if bot_response:
                            response_text, _ = bot_response
                            print(f"🤖 [BOT] {response_text[:80]}...")

                            # Guardar respuesta del bot en DB
                            save_message(
                                phone_number=phone_number,
                                content=response_text,
                                direction="outgoing"
                            )

                            # Enviar por WhatsApp si tenemos token
                            token = os.getenv("WHATSAPP_TOKEN")
                            phone_id = os.getenv("PHONE_NUMBER_ID")
                            if token and phone_id:
                                try:
                                    from whatsapp_client import WhatsAppClient
                                    client = WhatsAppClient()
                                    client.send_text_message(phone_number, response_text)
                                    print(f"✅ Respuesta enviada a {phone_number}")
                                except Exception as e:
                                    print(f"❌ Error enviando respuesta: {e}")
                            else:
                                print(f"⚠️  No se envió respuesta a {phone_number}: falta WHATSAPP_TOKEN o PHONE_NUMBER_ID en variables de entorno")

        print("=" * 60)
        return "OK", 200

    except Exception as e:
        print(f"❌ Error procesando webhook: {e}")
        return "OK", 200


# ============================================================
# INICIAR SERVIDOR
# ============================================================
if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║         🤖 D'MAR - CENTRO DE MANDO WHATSAPP              ║
    ║         (Delivery Máxima Atención Rider)                 ║
    ╠═══════════════════════════════════════════════════════════╣
    ║  🌐 Dashboard:  http://localhost:5000                     ║
    ║  🔗 Webhook:    http://localhost:5000/webhook             ║
    ║  🔑 Verify Token: {}                 ║
    ╚═══════════════════════════════════════════════════════════╝
    """.format(VERIFY_TOKEN))

    app.run(host="0.0.0.0", port=5000, debug=True)

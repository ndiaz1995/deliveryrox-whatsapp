from whatsapp_client import WhatsAppClient

def main():
    print("🚀 Prueba de envío de mensaje de WhatsApp")
    print("=" * 50)
    
    # Crear cliente
    client = WhatsAppClient()
    
    # Primero verificar que el token funcione
    print("\n🔍 Verificando token...")
    if not client.verify_token():
        print("\n⚠️  Tu token no es válido o falta el PHONE_NUMBER_ID.")
        print("Revisa tu archivo .env")
        return
    
    # Pedir datos al usuario
    print("\n📱 Ingresa el número al que quieres enviar el mensaje")
    print("   (Formato internacional sin +, ej: 5215512345678 para México)")
    number = input("Número: ").strip()
    
    message = input("\n💬 Escribe el mensaje a enviar: ").strip()
    
    if not number or not message:
        print("❌ Número y mensaje son obligatorios")
        return
    
    # Enviar mensaje
    try:
        result = client.send_text_message(number, message)
        print("\n📄 Respuesta de Meta:")
        print(result)
    except Exception as e:
        print(f"\n💥 Error: {e}")

if __name__ == "__main__":
    main()

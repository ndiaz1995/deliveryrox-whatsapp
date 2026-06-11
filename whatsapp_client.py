import requests
import json
import os
from config import WHATSAPP_TOKEN, PHONE_NUMBER_ID

class WhatsAppClient:
    """Cliente para interactuar con la API de WhatsApp Business de Meta."""
    
    BASE_URL = "https://graph.facebook.com/v25.0"
    
    def __init__(self):
        self.token = WHATSAPP_TOKEN
        self.phone_number_id = PHONE_NUMBER_ID
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def send_text_message(self, to_number: str, message: str) -> dict:
        """
        Envía un mensaje de texto a un número de WhatsApp.
        """
        url = f"{self.BASE_URL}/{self.phone_number_id}/messages"
        
        # Asegurarse que el número no tenga el signo +
        to_number = to_number.replace("+", "").replace(" ", "")
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_number,
            "type": "text",
            "text": {
                "body": message
            }
        }
        
        print(f"[WS-API] ===== ENVIO WHATSAPP =====")
        print(f"[WS-API] URL: {url}")
        print(f"[WS-API] Token presente: {bool(self.token)} (len={len(self.token) if self.token else 0})")
        print(f"[WS-API] Phone ID: {self.phone_number_id}")
        print(f"[WS-API] Destino: {to_number}")
        print(f"[WS-API] Mensaje: {message[:60]}...")
        
        response = requests.post(url, headers=self.headers, json=payload)
        
        print(f"[WS-API] Status: {response.status_code}")
        print(f"[WS-API] Respuesta: {response.text[:500]}")
        
        if response.status_code == 200:
            print("[WS-API] ✅ Mensaje enviado exitosamente!")
            return response.json()
        else:
            print(f"[WS-API] ❌ Error al enviar mensaje: {response.status_code}")
            response.raise_for_status()
    
    def get_business_profile(self) -> dict:
        """
        Obtiene la información del perfil de negocio.
        """
        url = f"{self.BASE_URL}/{self.phone_number_id}/whatsapp_business_profile"
        params = {"fields": "about,address,description,email,profile_picture_url,websites"}
        
        print("📋 Obteniendo perfil de negocio...")
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()
    
    def verify_token(self) -> bool:
        """
        Verifica que el token sea válido haciendo una petición simple.
        """
        try:
            self.get_business_profile()
            print("✅ Token válido y funcionando!")
            return True
        except Exception as e:
            print(f"❌ Error verificando token: {e}")
            return False

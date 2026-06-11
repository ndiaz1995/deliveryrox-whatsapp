"""
🤖 D'MAR Bot - Delivery Máxima Atención Rider
Motor de conversación automatizada con workflow inteligente.
"""

import json
from typing import Tuple, Optional
from database import (
    get_conversation_state, update_conversation_state,
    create_order, get_order
)


class DMARBot:
    """
    Bot conversacional para D'MAR.
    Maneja workflows de pedidos, consultas y atención al cliente.
    """

    # Estados del workflow
    STATES = {
        'welcome': 'bienvenida',
        'order_address': 'esperando_direccion',
        'order_product': 'esperando_producto',
        'order_confirm': 'confirmar_pedido',
        'track_order': 'consultar_pedido',
        'human_handoff': 'atencion_humana',
    }

    def __init__(self):
        self.welcome_message = (
            "🛵 *¡Bienvenido a D'MAR!*\n"
            "(Delivery Máxima Atención Rider)\n\n"
            "Gracias por comunicarte con nosotros. 😁\n"
            "¿Cómo podemos ayudarte hoy?\n\n"
            "*1.* 🛍️ Hacer un pedido\n"
            "*2.* 📦 Consultar estado de pedido\n"
            "*3.* 💬 Hablar con un humano"
        )

    def process_message(self, phone_number: str, message: str, profile_name: str = None) -> Tuple[str, Optional[str]]:
        """
        Procesa un mensaje entrante y retorna la respuesta del bot.
        
        Returns:
            (respuesta_texto, opcional_template_name)
        """
        message = message.strip().lower()
        state_data = get_conversation_state(phone_number)
        current_state = state_data['state']
        context = json.loads(state_data['context']) if state_data['context'] else {}

        # Si está en handoff humano, no respondemos automáticamente
        if state_data.get('human_handoff'):
            return None, None

        # Manejar estados
        if current_state == 'welcome':
            return self._handle_welcome(phone_number, message, context)
        elif current_state == 'order_address':
            return self._handle_order_address(phone_number, message, context)
        elif current_state == 'order_product':
            return self._handle_order_product(phone_number, message, context)
        elif current_state == 'order_confirm':
            return self._handle_order_confirm(phone_number, message, context)
        elif current_state == 'track_order':
            return self._handle_track_order(phone_number, message, context)
        elif current_state == 'human_handoff':
            return self._handle_human_handoff(phone_number, message, context)

        # Estado desconocido, reiniciar
        update_conversation_state(phone_number, 'welcome')
        return self.welcome_message, None

    def _handle_welcome(self, phone: str, msg: str, ctx: dict) -> Tuple[str, None]:
        """Maneja la bienvenida y opciones del menú."""
        if msg in ['1', 'pedido', 'hacer pedido', 'ordenar', 'quiero pedir']:
            update_conversation_state(phone, 'order_address', {})
            return (
                "🛍️ *¡Vamos a hacer tu pedido!*\n\n"
                "¿A qué dirección te lo llevamos? 📍\n"
                "_Ej: Calle 123, Edificio XYZ, Apto 4B_"
            ), None

        elif msg in ['2', 'estado', 'consultar', 'seguimiento', 'dónde está']:
            update_conversation_state(phone, 'track_order', {})
            return (
                "📦 *Consulta de pedido*\n\n"
                "Ingresa tu *número de pedido* 🔢\n"
                "_Ej: DMR240610143022_"
            ), None

        elif msg in ['3', 'humano', 'persona', 'operador', 'agente']:
            update_conversation_state(phone, 'human_handoff', {}, human_handoff=1)
            return (
                "💬 *Conectando con un operador...*\n\n"
                "🕐 Un momento por favor, te estamos transfiriendo "
                "con un agente de D'MAR.\n\n"
                "Mientras tanto, ¿algo más en lo que pueda ayudarte?"
            ), None

        else:
            # No entendió, repetir menú
            return (
                "🤔 No entendí tu respuesta.\n\n"
                + self.welcome_message
            ), None

    def _handle_order_address(self, phone: str, msg: str, ctx: dict) -> Tuple[str, None]:
        """Recibe la dirección del pedido."""
        if len(msg) < 5:
            return (
                "❌ La dirección parece muy corta.\n\n"
                "¿Podrías indicarnos una dirección completa? 📍\n"
                "_Ej: Av. Principal, Edificio Sol, Piso 3, Apto 3B_"
            ), None

        ctx['address'] = msg.strip()
        update_conversation_state(phone, 'order_product', ctx)
        return (
            "📍 *Dirección registrada:*\n"
            f"_{msg.strip()}_\n\n"
            "¿Qué necesitas pedir? 🍕🍔🥤\n"
            "_Ej: 2 hamburguesas con papas y 1 refresco grande_"
        ), None

    def _handle_order_product(self, phone: str, msg: str, ctx: dict) -> Tuple[str, None]:
        """Recibe el producto del pedido."""
        if len(msg) < 3:
            return (
                "❌ El pedido parece incompleto.\n\n"
                "¿Qué productos necesitas? 🍕🍔\n"
                "Sé lo más específico posible."
            ), None

        ctx['product'] = msg.strip()
        update_conversation_state(phone, 'order_confirm', ctx)

        return (
            "📋 *Resumen de tu pedido:*\n\n"
            f"📍 *Dirección:* {ctx['address']}\n"
            f"🛍️ *Pedido:* {ctx['product']}\n\n"
            "¿Todo correcto? Responde *sí* para confirmar o *no* para cancelar."
        ), None

    def _handle_order_confirm(self, phone: str, msg: str, ctx: dict) -> Tuple[str, None]:
        """Confirma o cancela el pedido."""
        if msg in ['sí', 'si', 'yes', 'confirmar', 'ok', 'dale']:
            order_code = create_order(phone, ctx['address'], ctx['product'])
            update_conversation_state(phone, 'welcome', {})

            return (
                f"🎉 *¡Pedido confirmado!*\n\n"
                f"Tu número de pedido es: *#{order_code}*\n\n"
                f"📍 {ctx['address']}\n"
                f"🛍️ {ctx['product']}\n\n"
                "⏱️ Te avisaremos cuando tu rider esté en camino.\n\n"
                "¿Algo más en lo que te pueda ayudar?\n"
                "*1.* Hacer otro pedido\n"
                "*2.* Consultar estado\n"
                "*3.* Hablar con humano"
            ), None

        elif msg in ['no', 'cancelar', 'nope', 'incorrecto']:
            update_conversation_state(phone, 'welcome', {})
            return (
                "❌ Pedido cancelado.\n\n"
                + self.welcome_message
            ), None

        else:
            return (
                "🤔 Por favor responde *sí* para confirmar tu pedido "
                "o *no* para cancelarlo."
            ), None

    def _handle_track_order(self, phone: str, msg: str, ctx: dict) -> Tuple[str, None]:
        """Consulta el estado de un pedido."""
        order = get_order(msg.upper().replace('#', ''))

        if order:
            status_emoji = {
                'pending': '⏳',
                'preparing': '👨‍🍳',
                'in_transit': '🛵',
                'delivered': '✅',
                'cancelled': '❌'
            }.get(order['status'], '📦')

            update_conversation_state(phone, 'welcome', {})
            return (
                f"{status_emoji} *Pedido #{order['order_code']}*\n\n"
                f"📍 *Dirección:* {order['address']}\n"
                f"🛍️ *Producto:* {order['product']}\n"
                f"📊 *Estado:* {order['status'].upper()}\n"
                f"📅 *Fecha:* {order['created_at'][:16]}\n\n"
                "¿Algo más en lo que te pueda ayudar?\n"
                "*1.* Hacer pedido  *2.* Consultar  *3.* Humano"
            ), None
        else:
            return (
                "❌ *No encontré ese pedido.*\n\n"
                "Verifica el número e intenta de nuevo.\n"
                "_Ej: DMR240610143022_\n\n"
                "O dime *cancelar* para volver al menú."
            ), None

    def _handle_human_handoff(self, phone: str, msg: str, ctx: dict) -> Tuple[str, None]:
        """Maneja mensajes cuando ya está en atención humana."""
        if msg in ['cancelar', 'salir', 'menu', 'menú', 'volver']:
            update_conversation_state(phone, 'welcome', {}, human_handoff=0)
            return self.welcome_message, None
        return None, None

    def reset_state(self, phone_number: str):
        """Reinicia la conversación al estado inicial."""
        update_conversation_state(phone_number, 'welcome', {}, human_handoff=0)

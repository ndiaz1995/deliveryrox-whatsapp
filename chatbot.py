"""
🤖 D'MAR Bot - Workflow Configurable
El bot lee su configuración desde SQLite y puede ser editado desde el panel.
"""

import json
import re
from typing import Tuple, Optional
from database import (
    get_conversation_state, update_conversation_state,
    create_order, get_order, get_bot_config
)


class DMARBot:
    """Bot con workflow 100% configurable desde la base de datos."""

    def __init__(self):
        self._load_config()

    def _load_config(self):
        """Carga el workflow desde SQLite."""
        config = get_bot_config()
        self.workflow = config.get("workflow", {})
        if not self.workflow:
            # Fallback si no hay configuración
            self.workflow = {
                "welcome": {
                    "message": "🛵 ¡Bienvenido a D'MAR!\n¿Cómo podemos ayudarte?",
                    "options": [
                        {"id": "order", "label": "Hacer pedido", "next": "ask_address"},
                        {"id": "human", "label": "Hablar con humano", "action": "handoff"}
                    ]
                }
            }

    def reload(self):
        """Recarga la configuración (útil después de editar)."""
        self._load_config()

    def process_message(self, phone_number: str, message: str, profile_name: str = None) -> Tuple[str, Optional[str]]:
        """Procesa un mensaje según el workflow configurado."""
        message = message.strip()
        state_data = get_conversation_state(phone_number)
        current_state = state_data['state']
        context = json.loads(state_data['context']) if state_data['context'] else {}

        # Si está en handoff humano, no respondemos
        if state_data.get('human_handoff'):
            return None, None

        # Si el usuario dice "menu", "inicio", "volver", reiniciamos
        if message.lower() in ['menu', 'inicio', 'volver', 'salir', 'cancelar', '0']:
            update_conversation_state(phone_number, 'welcome', {})
            return self._render_state('welcome', context), None

        # Obtener configuración del estado actual
        state_config = self.workflow.get(current_state)
        
        if not state_config:
            # Estado desconocido, volver a welcome
            update_conversation_state(phone_number, 'welcome', {})
            return self._render_state('welcome', context), None

        # Si el estado tiene opciones (menú), verificar selección
        options = state_config.get('options', [])
        if options:
            selected = self._match_option(message, options)
            if selected:
                # Ejecutar acción si tiene
                if selected.get('action') == 'handoff':
                    update_conversation_state(phone_number, 'human_handoff', {}, human_handoff=1)
                    return "🕐 Te estamos conectando con un operador de D'MAR. Un momento por favor...", None
                
                if selected.get('action') == 'create_order':
                    return self._create_order_action(phone_number, context)
                
                # Ir al siguiente estado
                next_state = selected.get('next', 'welcome')
                update_conversation_state(phone_number, next_state, context)
                return self._render_state(next_state, context), None
            
            # No seleccionó una opción válida
            return self._render_state(current_state, context), None

        # Si el estado tiene "save_as", guardamos lo que escribió
        if state_config.get('save_as'):
            context[state_config['save_as']] = message
            
            # Ejecutar acción si tiene
            if state_config.get('action') == 'create_order':
                return self._create_order_action(phone_number, context)
            
            if state_config.get('action') == 'show_order':
                return self._show_order_action(phone_number, context)
            
            # Ir al siguiente estado
            next_state = state_config.get('next', 'welcome')
            update_conversation_state(phone_number, next_state, context)
            return self._render_state(next_state, context), None

        # Estado con acción especial sin guardar
        if state_config.get('action') == 'show_order':
            return self._show_order_action(phone_number, context)

        # Estado normal, ir al siguiente
        next_state = state_config.get('next', 'welcome')
        update_conversation_state(phone_number, next_state, context)
        return self._render_state(next_state, context), None

    def _match_option(self, message: str, options: list) -> Optional[dict]:
        """Intenta hacer match del mensaje con una opción."""
        msg_lower = message.lower()
        
        for opt in options:
            # Match por número: "1", "2", "3"
            if msg_lower == str(options.index(opt) + 1):
                return opt
            # Match por ID exacto
            if msg_lower == opt['id'].lower():
                return opt
            # Match por primera palabra del label
            label_words = opt['label'].lower().split()
            if label_words and msg_lower == label_words[0]:
                return opt
        
        return None

    def _render_state(self, state_id: str, context: dict) -> str:
        """Renderiza el mensaje de un estado reemplazando variables."""
        state_config = self.workflow.get(state_id)
        if not state_config:
            return "🛵 ¿Cómo podemos ayudarte?"
        
        message = state_config.get('message', '')
        
        # Reemplazar variables {{nombre}}
        for key, value in context.items():
            message = message.replace(f'{{{{{key}}}}}', str(value))
        
        # Agregar opciones si las hay
        options = state_config.get('options', [])
        if options:
            message += "\n\n"
            for i, opt in enumerate(options, 1):
                message += f"*{i}.* {opt['label']}\n"
        
        return message

    def _create_order_action(self, phone_number: str, context: dict) -> Tuple[str, None]:
        """Crea un pedido y retorna mensaje de confirmación."""
        address = context.get('address', 'Sin dirección')
        product = context.get('product', 'Sin producto')
        
        order_code = create_order(phone_number, address, product)
        context['order_code'] = order_code
        
        update_conversation_state(phone_number, 'welcome', {})
        
        # Buscar mensaje de confirmación en workflow
        confirm_state = self.workflow.get('order_created')
        if confirm_state:
            return self._render_state('order_created', context), None
        
        return f"🎉 ¡Pedido confirmado!\nTu número es: #{order_code}", None

    def _show_order_action(self, phone_number: str, context: dict) -> Tuple[str, None]:
        """Busca un pedido y muestra su estado."""
        code = context.get('order_code', '').upper().replace('#', '')
        
        if not code:
            update_conversation_state(phone_number, 'ask_order_code', context)
            return self._render_state('ask_order_code', context), None
        
        order = get_order(code)
        
        if order:
            status = order['status'].upper()
            emoji = {'PENDING': '⏳', 'PREPARING': '👨‍🍳', 'IN_TRANSIT': '🛵', 'DELIVERED': '✅', 'CANCELLED': '❌'}.get(status, '📦')
            
            update_conversation_state(phone_number, 'welcome', {})
            
            return (
                f"{emoji} *Pedido #{order['order_code']}*\n\n"
                f"📍 {order['address']}\n"
                f"🛍️ {order['product']}\n"
                f"📊 Estado: {status}\n\n"
                f"¿Algo más? Escribe *menu*"
            ), None
        else:
            update_conversation_state(phone_number, 'order_not_found', context)
            return self._render_state('order_not_found', context), None

    def reset_state(self, phone_number: str):
        """Reinicia la conversación."""
        update_conversation_state(phone_number, 'welcome', {}, human_handoff=0)

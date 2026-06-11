"""
🤖 D'MAR Bot - Motor de Ejecución de Nodos
El bot ejecuta un workflow de nodos conectados, avanzando paso a paso
según las respuestas del usuario.
"""

import json
from typing import Tuple, Optional
from database import (
    get_conversation_state, update_conversation_state,
    create_order, get_order, get_bot_config
)


class DMARBot:
    """
    Motor de ejecución de workflow basado en nodos.
    Cada conversación tiene un 'current_node' que avanza según el flujo.
    """

    def __init__(self):
        self._load_config()

    def _load_config(self):
        """Carga el workflow ejecutable desde SQLite."""
        config = get_bot_config()
        workflow = config.get("executable", {})
        self.start_node = workflow.get("start_node", "")
        self.nodes = workflow.get("nodes", {})
        
        if not self.nodes:
            # Fallback por defecto
            self.start_node = "welcome"
            self.nodes = {
                "welcome": {
                    "type": "message",
                    "content": "🛵 ¡Bienvenido a D'MAR!\n¿Cómo podemos ayudarte?",
                    "next": "menu"
                },
                "menu": {
                    "type": "options",
                    "content": "Elige una opción:",
                    "options": [
                        {"id": "pedido", "label": "🛍️ Hacer pedido", "next": "ask_item"},
                        {"id": "human", "label": "💬 Hablar con humano", "next": "handoff"}
                    ]
                },
                "ask_item": {
                    "type": "input",
                    "content": "¿Qué necesitas pedir?",
                    "save_as": "item",
                    "next": "ask_address"
                },
                "ask_address": {
                    "type": "input",
                    "content": "¿A qué dirección?",
                    "save_as": "address",
                    "next": "create_order"
                },
                "create_order": {
                    "type": "action",
                    "action": "create_order",
                    "next": "confirm"
                },
                "confirm": {
                    "type": "message",
                    "content": "🎉 ¡Pedido creado! #{{order_code}}\n📍 {{address}}\n🛍️ {{item}}"
                },
                "handoff": {
                    "type": "action",
                    "action": "handoff"
                }
            }

    def reload(self):
        """Recarga la configuración del workflow."""
        self._load_config()

    def process_message(self, phone_number: str, message: str, profile_name: str = None) -> Tuple[str, Optional[str]]:
        """
        Procesa un mensaje ejecutando el workflow nodo a nodo.
        
        Returns:
            (respuesta_texto, None) o (None, None) si no responde
        """
        message = message.strip()
        state_data = get_conversation_state(phone_number)
        current_node_id = state_data.get('current_node') or self.start_node
        context = json.loads(state_data['context']) if state_data.get('context') else {}

        # Si está en handoff humano, no respondemos automáticamente
        if state_data.get('human_handoff'):
            return None, None

        # Comandos especiales del usuario
        msg_lower = message.lower()
        if msg_lower in ['menu', 'inicio', 'volver', 'salir', 'cancelar', '0', 'reiniciar']:
            update_conversation_state(phone_number, self.start_node, context)
            return self._execute_node(self.start_node, context), None

        # Obtener configuración del nodo actual
        node_config = self.nodes.get(current_node_id)
        if not node_config:
            # Nodo no existe, reiniciar
            update_conversation_state(phone_number, self.start_node, context)
            return self._execute_node(self.start_node, context), None

        node_type = node_config.get('type', 'message')

        # ===== EJECUTAR SEGÚN TIPO DE NODO =====
        
        if node_type == 'message':
            # Mensaje de una vía: enviar y avanzar
            response = self._render_content(node_config.get('content', ''), context)
            next_node = node_config.get('next')
            if next_node:
                update_conversation_state(phone_number, next_node, context)
                # Si el siguiente también es mensaje, ejecutarlo también (encadenar)
                return self._chain_messages(next_node, context, response)
            return response, None

        elif node_type == 'start':
            # Igual que message pero es el punto de entrada
            response = self._render_content(node_config.get('content', ''), context)
            next_node = node_config.get('next')
            if next_node:
                update_conversation_state(phone_number, next_node, context)
                return self._chain_messages(next_node, context, response)
            return response, None

        elif node_type == 'options':
            # Mostrar menú y esperar selección
            selected = self._match_option(message, node_config.get('options', []))
            
            if selected:
                # Usuario eligió una opción válida
                next_node = selected.get('next')
                if next_node:
                    update_conversation_state(phone_number, next_node, context)
                    return self._execute_node(next_node, context), None
                else:
                    # Opción sin destino, mostrar menú de nuevo
                    return self._execute_node(current_node_id, context), None
            else:
                # No entendió, repetir el menú
                return self._execute_node(current_node_id, context), None

        elif node_type == 'input':
            # Guardar respuesta del usuario
            save_as = node_config.get('save_as', 'response')
            context[save_as] = message
            
            next_node = node_config.get('next')
            if next_node:
                update_conversation_state(phone_number, next_node, context)
                return self._execute_node(next_node, context), None
            return None, None

        elif node_type == 'condition':
            # Evaluar condición
            condition_type = node_config.get('condition', 'yes_no')
            next_node = None
            
            if condition_type == 'yes_no':
                if msg_lower in ['sí', 'si', 'yes', 'ok', 'dale', 'confirmar']:
                    next_node = node_config.get('next_true')
                elif msg_lower in ['no', 'nope', 'cancelar']:
                    next_node = node_config.get('next_false')
            
            elif condition_type == 'equals':
                # Comparar con valor esperado (podría venir de contexto)
                expected = node_config.get('expected_value', '').lower()
                if msg_lower == expected:
                    next_node = node_config.get('next_true')
                else:
                    next_node = node_config.get('next_false')
            
            elif condition_type == 'contains':
                expected = node_config.get('expected_value', '').lower()
                if expected in msg_lower:
                    next_node = node_config.get('next_true')
                else:
                    next_node = node_config.get('next_false')
            
            if next_node:
                update_conversation_state(phone_number, next_node, context)
                return self._execute_node(next_node, context), None
            else:
                # No cumplió condición, repetir
                return self._execute_node(current_node_id, context), None

        elif node_type == 'action':
            # Ejecutar acción y avanzar
            action = node_config.get('action', 'create_order')
            
            if action == 'create_order':
                return self._action_create_order(phone_number, context, node_config)
            
            elif action == 'handoff':
                update_conversation_state(phone_number, current_node_id, context, human_handoff=1)
                return "🕐 Te estamos conectando con un operador de D'MAR. Un momento por favor...", None
            
            elif action == 'show_order':
                return self._action_show_order(phone_number, context, node_config)
            
            # Acción desconocida, avanzar al siguiente
            next_node = node_config.get('next')
            if next_node:
                update_conversation_state(phone_number, next_node, context)
                return self._execute_node(next_node, context), None
            return None, None

        # Tipo desconocido, reiniciar
        update_conversation_state(phone_number, self.start_node, context)
        return self._execute_node(self.start_node, context), None

    def _execute_node(self, node_id: str, context: dict) -> str:
        """Ejecuta un nodo y retorna su mensaje renderizado (sin avanzar)."""
        node = self.nodes.get(node_id)
        if not node:
            return "🛵 ¿Cómo podemos ayudarte?"
        
        content = self._render_content(node.get('content', ''), context)
        
        # Agregar opciones si es menú
        if node.get('type') == 'options':
            options = node.get('options', [])
            if options:
                content += "\n\n"
                for i, opt in enumerate(options, 1):
                    content += f"*{i}.* {opt['label']}\n"
        
        return content

    def _chain_messages(self, node_id: str, context: dict, accumulated: str) -> str:
        """
        Si un mensaje va a otro mensaje, encadena las respuestas.
        Evita enviar 3 mensajes separados cuando hay 3 mensajes seguidos.
        """
        node = self.nodes.get(node_id)
        if not node:
            return accumulated
        
        if node.get('type') in ['message', 'start']:
            # Encadenar contenido
            content = self._render_content(node.get('content', ''), context)
            accumulated += "\n\n" + content
            
            # Avanzar al siguiente
            next_node = node.get('next')
            if next_node:
                # Actualizar estado para que apunte al siguiente
                # Pero no podemos acceder a phone_number aquí...
                # Por ahora solo encadenamos 1 nivel
                pass
            return accumulated
        
        return accumulated

    def _render_content(self, content: str, context: dict) -> str:
        """Reemplaza variables {{nombre}} en el contenido."""
        if not content:
            return ""
        for key, value in context.items():
            content = content.replace(f'{{{{{key}}}}}', str(value))
        return content

    def _match_option(self, message: str, options: list) -> Optional[dict]:
        """Intenta hacer match del mensaje con una opción del menú."""
        msg_lower = message.lower()
        
        for i, opt in enumerate(options):
            opt_id = opt.get('id', '').lower()
            opt_label = opt.get('label', '').lower()
            
            # Match por número: "1", "2", "3"
            if msg_lower == str(i + 1):
                return opt
            
            # Match por ID
            if msg_lower == opt_id:
                return opt
            
            # Match por primera palabra del label
            label_words = opt_label.split()
            if label_words and msg_lower == label_words[0]:
                return opt
            
            # Match por label completo
            if msg_lower == opt_label:
                return opt
        
        return None

    def _action_create_order(self, phone_number: str, context: dict, node_config: dict) -> Tuple[str, None]:
        """Ejecuta la acción de crear pedido."""
        address = context.get('address', 'Sin dirección')
        product = context.get('item', context.get('product', 'Sin producto'))
        
        order_code = create_order(phone_number, address, product)
        context['order_code'] = order_code
        
        # Buscar siguiente nodo
        next_node = node_config.get('next')
        if next_node:
            update_conversation_state(phone_number, next_node, context)
            return self._execute_node(next_node, context), None
        
        return f"🎉 ¡Pedido confirmado!\nTu número es: #{order_code}", None

    def _action_show_order(self, phone_number: str, context: dict, node_config: dict) -> Tuple[str, None]:
        """Ejecuta la acción de mostrar pedido."""
        code = context.get('order_code', '').upper().replace('#', '')
        
        if not code:
            # Volver a pedir código
            return "🔢 Por favor ingresa tu número de pedido:", None
        
        order = get_order(code)
        
        if order:
            status = order['status'].upper()
            emoji = {'PENDING': '⏳', 'PREPARING': '👨‍🍳', 'IN_TRANSIT': '🛵', 'DELIVERED': '✅', 'CANCELLED': '❌'}.get(status, '📦')
            
            next_node = node_config.get('next')
            if next_node:
                update_conversation_state(phone_number, next_node, context)
            else:
                update_conversation_state(phone_number, self.start_node, context)
            
            return (
                f"{emoji} *Pedido #{order['order_code']}*\n\n"
                f"📍 {order['address']}\n"
                f"🛍️ {order['product']}\n"
                f"📊 Estado: {status}\n\n"
                f"¿Algo más? Escribe *menu*"
            ), None
        else:
            return "❌ No encontré ese pedido. Verifica el número o escribe *menu*.", None

    def reset_state(self, phone_number: str):
        """Reinicia la conversación al nodo inicial."""
        update_conversation_state(phone_number, self.start_node, {}, human_handoff=0)

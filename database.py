import sqlite3
from datetime import datetime
from typing import List, Dict, Optional

DATABASE = "whatsapp_center.db"


def init_db():
    """Inicializa la base de datos con las tablas necesarias."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Tabla de contactos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone_number TEXT UNIQUE NOT NULL,
            name TEXT,
            profile_name TEXT,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            message_count INTEGER DEFAULT 0
        )
    """)

    # Tabla de mensajes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone_number TEXT NOT NULL,
            message_id TEXT UNIQUE,
            content TEXT NOT NULL,
            message_type TEXT DEFAULT 'text',
            timestamp TEXT NOT NULL,
            status TEXT DEFAULT 'new',
            direction TEXT DEFAULT 'incoming'
        )
    """)

    # Tabla de conversaciones
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone_number TEXT UNIQUE NOT NULL,
            last_message TEXT,
            last_message_time TEXT,
            unread_count INTEGER DEFAULT 0,
            total_messages INTEGER DEFAULT 0
        )
    """)

    # Tabla de estados del bot (workflow)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversation_states (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone_number TEXT UNIQUE NOT NULL,
            state TEXT DEFAULT 'welcome',
            context TEXT DEFAULT '{}',
            updated_at TEXT NOT NULL,
            human_handoff INTEGER DEFAULT 0
        )
    """)

    # Tabla de pedidos (orders)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone_number TEXT NOT NULL,
            order_code TEXT UNIQUE NOT NULL,
            address TEXT NOT NULL,
            product TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    # Tabla de configuración del bot (workflow)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bot_config (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            workflow TEXT NOT NULL,
            executable TEXT,
            welcome_message TEXT,
            updated_at TEXT NOT NULL
        )
    """)
    
    # Migrar: agregar columna executable si no existe (para bases antiguas)
    try:
        cursor.execute("SELECT executable FROM bot_config LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE bot_config ADD COLUMN executable TEXT")
    
    # Insertar workflow por defecto si no existe
    cursor.execute("SELECT COUNT(*) FROM bot_config")
    if cursor.fetchone()[0] == 0:
        import json
        default_workflow = {
            "welcome": {
                "message": "🛵 *¡Bienvenido a D'MAR!*\n(Delivery Máxima Atención Rider)\n\nGracias por comunicarte con nosotros. 😁\n¿Cómo podemos ayudarte hoy?",
                "options": [
                    {"id": "order", "label": "🛍️ Hacer un pedido", "next": "ask_address"},
                    {"id": "track", "label": "📦 Consultar pedido", "next": "ask_order_code"},
                    {"id": "human", "label": "💬 Hablar con humano", "action": "handoff"}
                ]
            },
            "ask_address": {
                "message": "📍 *¿A qué dirección te lo llevamos?*\n\n_Ej: Av. Principal, Edificio Sol, Piso 3_",
                "next": "ask_product",
                "save_as": "address"
            },
            "ask_product": {
                "message": "🍕 *¿Qué necesitas pedir?*\n\n_Ej: 2 hamburguesas con papas y 1 refresco_",
                "next": "confirm_order",
                "save_as": "product"
            },
            "confirm_order": {
                "message": "📋 *Resumen de tu pedido:*\n\n📍 *Dirección:* {{address}}\n🛍️ *Pedido:* {{product}}\n\n¿Todo correcto?",
                "options": [
                    {"id": "yes", "label": "✅ Sí, confirmar", "action": "create_order"},
                    {"id": "no", "label": "❌ No, cancelar", "next": "welcome"}
                ]
            },
            "ask_order_code": {
                "message": "📦 *Consulta de pedido*\n\nIngresa tu *número de pedido* 🔢\n_Ej: DMR240610143022_",
                "next": "show_order_status",
                "save_as": "order_code"
            },
            "show_order_status": {
                "message": "🔍 Buscando pedido...",
                "action": "show_order"
            },
            "order_created": {
                "message": "🎉 *¡Pedido confirmado!*\n\nTu número de pedido es: *#{{order_code}}*\n\n📍 {{address}}\n🛍️ {{product}}\n\n⏱️ Te avisaremos cuando tu rider esté en camino.",
                "next": "welcome"
            },
            "order_not_found": {
                "message": "❌ *No encontré ese pedido.*\n\nVerifica el número e intenta de nuevo.\n_O dime *menu* para volver al inicio._",
                "next": "ask_order_code"
            }
        }
        now = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO bot_config (id, workflow, executable, welcome_message, updated_at)
            VALUES (1, ?, ?, ?, ?)
        """, (json.dumps(default_workflow), json.dumps(default_workflow), default_workflow["welcome"]["message"], now))

    conn.commit()
    conn.close()


def save_message(phone_number: str, content: str, message_id: str = None,
                 message_type: str = 'text', timestamp: str = None,
                 direction: str = 'incoming', profile_name: str = None) -> bool:
    """Guarda un mensaje y actualiza contactos/conversaciones."""
    if timestamp is None:
        timestamp = datetime.now().isoformat()

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    if message_id:
        cursor.execute("SELECT id FROM messages WHERE message_id = ?", (message_id,))
        if cursor.fetchone():
            conn.close()
            return False

    cursor.execute("""
        INSERT INTO messages (phone_number, message_id, content, message_type, timestamp, status, direction)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (phone_number, message_id, content, message_type, timestamp, 'new', direction))

    cursor.execute("SELECT * FROM contacts WHERE phone_number = ?", (phone_number,))
    contact = cursor.fetchone()

    if contact:
        cursor.execute("""
            UPDATE contacts SET last_seen = ?, message_count = message_count + 1
            WHERE phone_number = ?
        """, (timestamp, phone_number))
    else:
        cursor.execute("""
            INSERT INTO contacts (phone_number, profile_name, first_seen, last_seen, message_count)
            VALUES (?, ?, ?, ?, 1)
        """, (phone_number, profile_name, timestamp, timestamp))

    cursor.execute("SELECT * FROM conversations WHERE phone_number = ?", (phone_number,))
    conv = cursor.fetchone()

    if conv:
        cursor.execute("""
            UPDATE conversations 
            SET last_message = ?, last_message_time = ?, unread_count = unread_count + 1, total_messages = total_messages + 1
            WHERE phone_number = ?
        """, (content, timestamp, phone_number))
    else:
        cursor.execute("""
            INSERT INTO conversations (phone_number, last_message, last_message_time, unread_count, total_messages)
            VALUES (?, ?, ?, 1, 1)
        """, (phone_number, content, timestamp))

    conn.commit()
    conn.close()
    return True


# ========== ESTADOS DEL BOT ==========

def get_conversation_state(phone_number: str) -> Dict:
    """Obtiene el estado actual de una conversación."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM conversation_states WHERE phone_number = ?", (phone_number,))
    row = cursor.fetchone()

    if not row:
        now = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO conversation_states (phone_number, state, current_node, context, updated_at)
            VALUES (?, 'active', NULL, '{}', ?)
        """, (phone_number, now))
        conn.commit()
        conn.close()
        return {"phone_number": phone_number, "state": "active", "current_node": None, "context": "{}", "human_handoff": 0}

    conn.close()
    return dict(row)


def update_conversation_state(phone_number: str, current_node: str, context: dict = None, human_handoff: int = None):
    """Actualiza el estado de una conversación (usa current_node en vez de state)."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    now = datetime.now().isoformat()
    ctx = str(context) if context else "{}"

    if human_handoff is not None:
        cursor.execute("""
            INSERT INTO conversation_states (phone_number, state, current_node, context, updated_at, human_handoff)
            VALUES (?, 'active', ?, ?, ?, ?)
            ON CONFLICT(phone_number) DO UPDATE SET
                current_node = excluded.current_node,
                context = excluded.context,
                updated_at = excluded.updated_at,
                human_handoff = excluded.human_handoff
        """, (phone_number, current_node, ctx, now, human_handoff))
    else:
        cursor.execute("""
            INSERT INTO conversation_states (phone_number, state, current_node, context, updated_at)
            VALUES (?, 'active', ?, ?, ?)
            ON CONFLICT(phone_number) DO UPDATE SET
                current_node = excluded.current_node,
                context = excluded.context,
                updated_at = excluded.updated_at
        """, (phone_number, current_node, ctx, now))

    conn.commit()
    conn.close()


# ========== PEDIDOS ==========

def create_order(phone_number: str, address: str, product: str) -> str:
    """Crea un nuevo pedido y retorna su código."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    now = datetime.now().isoformat()
    order_code = f"DMR{datetime.now().strftime('%y%m%d%H%M%S')}"

    cursor.execute("""
        INSERT INTO orders (phone_number, order_code, address, product, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, 'pending', ?, ?)
    """, (phone_number, order_code, address, product, now, now))

    conn.commit()
    conn.close()
    return order_code


def get_order(order_code: str) -> Optional[Dict]:
    """Busca un pedido por su código."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM orders WHERE order_code = ?", (order_code.upper(),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_orders_by_phone(phone_number: str) -> List[Dict]:
    """Obtiene todos los pedidos de un número."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM orders WHERE phone_number = ? ORDER BY created_at DESC", (phone_number,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ========== MENSAJES Y CONVERSACIONES ==========

def get_messages(phone_number: str = None, limit: int = 50) -> List[Dict]:
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if phone_number:
        cursor.execute("""
            SELECT * FROM messages WHERE phone_number = ? ORDER BY timestamp DESC LIMIT ?
        """, (phone_number, limit))
    else:
        cursor.execute("""
            SELECT * FROM messages ORDER BY timestamp DESC LIMIT ?
        """, (limit,))

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_conversations() -> List[Dict]:
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT c.*, co.profile_name, st.state, st.human_handoff
        FROM conversations c
        LEFT JOIN contacts co ON c.phone_number = co.phone_number
        LEFT JOIN conversation_states st ON c.phone_number = st.phone_number
        ORDER BY c.last_message_time DESC
    """)

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_contacts() -> List[Dict]:
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM contacts ORDER BY last_seen DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_stats() -> Dict:
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM contacts")
    total_contacts = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM messages WHERE direction = 'incoming'")
    total_messages = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM conversations WHERE unread_count > 0")
    unread_conversations = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM messages 
        WHERE direction = 'incoming' AND timestamp > datetime('now', '-24 hours')
    """)
    messages_today = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'pending'")
    pending_orders = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM conversation_states WHERE human_handoff = 1")
    human_handoffs = cursor.fetchone()[0]

    conn.close()

    return {
        "total_contacts": total_contacts,
        "total_messages": total_messages,
        "unread_conversations": unread_conversations,
        "messages_today": messages_today,
        "pending_orders": pending_orders,
        "human_handoffs": human_handoffs
    }


def mark_conversation_as_read(phone_number: str):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("UPDATE messages SET status = 'read' WHERE phone_number = ? AND status = 'new'", (phone_number,))
    cursor.execute("UPDATE conversations SET unread_count = 0 WHERE phone_number = ?", (phone_number,))
    conn.commit()
    conn.close()


# ========== CONFIGURACIÓN DEL BOT ==========

def get_bot_config() -> Dict:
    """Obtiene la configuración del bot (visual + ejecutable)."""
    import json
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bot_config WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    
    if row:
        visual = json.loads(row["workflow"]) if row["workflow"] else {}
        try:
            executable = json.loads(row["executable"]) if row["executable"] else {}
        except (KeyError, TypeError):
            executable = {}
        return {
            "visual": visual,
            "executable": executable,
            "welcome_message": row["welcome_message"],
            "updated_at": row["updated_at"]
        }
    return {"visual": {}, "executable": {}, "welcome_message": "", "updated_at": ""}


def save_bot_config(visual: dict = None, executable: dict = None, welcome_message: str = None):
    """Guarda la configuración del bot (ambos formatos)."""
    import json
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    
    # Obtener config actual para merge
    cursor.execute("SELECT workflow, executable, welcome_message FROM bot_config WHERE id = 1")
    row = cursor.fetchone()
    
    current_visual = json.loads(row[0]) if row and row[0] else {}
    current_executable = json.loads(row[1]) if row and row[1] else {}
    current_welcome = row[2] if row and row[2] else ""
    
    visual_data = json.dumps(visual) if visual else json.dumps(current_visual)
    executable_data = json.dumps(executable) if executable else json.dumps(current_executable)
    welcome = welcome_message or current_welcome
    
    cursor.execute("""
        INSERT INTO bot_config (id, workflow, executable, welcome_message, updated_at)
        VALUES (1, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            workflow = excluded.workflow,
            executable = excluded.executable,
            welcome_message = excluded.welcome_message,
            updated_at = excluded.updated_at
    """, (visual_data, executable_data, welcome, now))
    
    conn.commit()
    conn.close()


def get_contact(phone_number: str) -> Optional[Dict]:
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM contacts WHERE phone_number = ?", (phone_number,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

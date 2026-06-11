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
            INSERT INTO conversation_states (phone_number, state, context, updated_at)
            VALUES (?, 'welcome', '{}', ?)
        """, (phone_number, now))
        conn.commit()
        conn.close()
        return {"phone_number": phone_number, "state": "welcome", "context": "{}", "human_handoff": 0}

    conn.close()
    return dict(row)


def update_conversation_state(phone_number: str, state: str, context: dict = None, human_handoff: int = None):
    """Actualiza el estado de una conversación."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    now = datetime.now().isoformat()
    ctx = str(context) if context else "{}"

    if human_handoff is not None:
        cursor.execute("""
            INSERT INTO conversation_states (phone_number, state, context, updated_at, human_handoff)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(phone_number) DO UPDATE SET
                state = excluded.state,
                context = excluded.context,
                updated_at = excluded.updated_at,
                human_handoff = excluded.human_handoff
        """, (phone_number, state, ctx, now, human_handoff))
    else:
        cursor.execute("""
            INSERT INTO conversation_states (phone_number, state, context, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(phone_number) DO UPDATE SET
                state = excluded.state,
                context = excluded.context,
                updated_at = excluded.updated_at
        """, (phone_number, state, ctx, now))

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


def get_contact(phone_number: str) -> Optional[Dict]:
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM contacts WHERE phone_number = ?", (phone_number,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

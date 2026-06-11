import sqlite3
from datetime import datetime
from typing import List, Dict, Optional

DATABASE = "whatsapp_center.db"


def init_db():
    """Inicializa la base de datos con las tablas necesarias."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Tabla de contactos (números que nos escribieron)
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

    # Tabla de mensajes recibidos
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

    # Tabla de conversaciones (resumen por contacto)
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

    conn.commit()
    conn.close()


def save_message(phone_number: str, content: str, message_id: str = None,
                 message_type: str = 'text', timestamp: str = None,
                 direction: str = 'incoming', profile_name: str = None) -> bool:
    """
    Guarda un mensaje en la base de datos y actualiza contactos/conversaciones.
    Retorna True si es un mensaje nuevo, False si ya existía.
    """
    if timestamp is None:
        timestamp = datetime.now().isoformat()

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Verificar si el mensaje ya existe (evitar duplicados)
    if message_id:
        cursor.execute("SELECT id FROM messages WHERE message_id = ?", (message_id,))
        if cursor.fetchone():
            conn.close()
            return False

    # Guardar el mensaje
    cursor.execute("""
        INSERT INTO messages (phone_number, message_id, content, message_type, timestamp, status, direction)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (phone_number, message_id, content, message_type, timestamp, 'new', direction))

    # Actualizar o crear contacto
    cursor.execute("SELECT * FROM contacts WHERE phone_number = ?", (phone_number,))
    contact = cursor.fetchone()

    if contact:
        cursor.execute("""
            UPDATE contacts 
            SET last_seen = ?, message_count = message_count + 1
            WHERE phone_number = ?
        """, (timestamp, phone_number))
    else:
        cursor.execute("""
            INSERT INTO contacts (phone_number, profile_name, first_seen, last_seen, message_count)
            VALUES (?, ?, ?, ?, 1)
        """, (phone_number, profile_name, timestamp, timestamp))

    # Actualizar o crear conversación
    cursor.execute("SELECT * FROM conversations WHERE phone_number = ?", (phone_number,))
    conv = cursor.fetchone()

    if conv:
        cursor.execute("""
            UPDATE conversations 
            SET last_message = ?, last_message_time = ?, 
                unread_count = unread_count + 1,
                total_messages = total_messages + 1
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


def get_messages(phone_number: str = None, limit: int = 50) -> List[Dict]:
    """Obtiene mensajes, opcionalmente filtrados por número."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if phone_number:
        cursor.execute("""
            SELECT * FROM messages 
            WHERE phone_number = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (phone_number, limit))
    else:
        cursor.execute("""
            SELECT * FROM messages 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (limit,))

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_conversations() -> List[Dict]:
    """Obtiene todas las conversaciones activas ordenadas por más recientes."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT c.*, co.profile_name 
        FROM conversations c
        LEFT JOIN contacts co ON c.phone_number = co.phone_number
        ORDER BY c.last_message_time DESC
    """)

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_contacts() -> List[Dict]:
    """Obtiene todos los contactos."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM contacts ORDER BY last_seen DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_stats() -> Dict:
    """Obtiene estadísticas del centro de mando."""
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
        WHERE direction = 'incoming' 
        AND timestamp > datetime('now', '-24 hours')
    """)
    messages_today = cursor.fetchone()[0]

    conn.close()

    return {
        "total_contacts": total_contacts,
        "total_messages": total_messages,
        "unread_conversations": unread_conversations,
        "messages_today": messages_today
    }


def mark_conversation_as_read(phone_number: str):
    """Marca todos los mensajes de un número como leídos."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE messages SET status = 'read' 
        WHERE phone_number = ? AND status = 'new'
    """, (phone_number,))

    cursor.execute("""
        UPDATE conversations SET unread_count = 0 
        WHERE phone_number = ?
    """, (phone_number,))

    conn.commit()
    conn.close()


def get_contact(phone_number: str) -> Optional[Dict]:
    """Obtiene información de un contacto específico."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM contacts WHERE phone_number = ?", (phone_number,))
    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None

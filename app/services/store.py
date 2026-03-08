import sqlite3
from typing import Optional, List, Tuple, Dict, Any


class StoreService:
    def __init__(self, db_url: str = "sqlite:///./data.db"):
        self.path = db_url.replace("sqlite:///", "")
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.path)
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                sender TEXT,
                text TEXT,
                reply TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                scheduled_at TEXT,
                metadata TEXT,
                is_active INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    # ─── Messages ────────────────────────────────────────────────

    def is_already_replied(self, message_id: str) -> bool:
        conn = sqlite3.connect(self.path)
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM messages WHERE id = ? AND reply IS NOT NULL", (message_id,))
        row = cur.fetchone()
        conn.close()
        return row is not None

    def save_message(self, message_id: str, sender: str, text: str, reply: Optional[str] = None):
        conn = sqlite3.connect(self.path)
        cur = conn.cursor()
        cur.execute(
            "REPLACE INTO messages (id, sender, text, reply) VALUES (?, ?, ?, ?)",
            (message_id, sender, text, reply),
        )
        conn.commit()
        conn.close()

    def get_conversation(self, message_id: str) -> List[Tuple[str, str]]:
        conn = sqlite3.connect(self.path)
        cur = conn.cursor()
        cur.execute("SELECT sender, text FROM messages WHERE id = ? ORDER BY created_at ASC", (message_id,))
        rows = cur.fetchall()
        conn.close()
        return rows

    def get_all_messages(self) -> List[Dict[str, Any]]:
        """Retorna todas as mensagens processadas, do mais recente ao mais antigo"""
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT id, sender, text, reply, created_at FROM messages ORDER BY created_at DESC")
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    def has_reply(self, message_id: str) -> bool:
        return self.is_already_replied(message_id)

    # ─── Config ──────────────────────────────────────────────────

    def get_config(self, key: str) -> Optional[str]:
        conn = sqlite3.connect(self.path)
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = ?", (key,))
        row = cur.fetchone()
        conn.close()
        return row[0] if row else None

    def get_all_config(self) -> Dict[str, str]:
        conn = sqlite3.connect(self.path)
        cur = conn.cursor()
        cur.execute("SELECT key, value FROM config")
        rows = cur.fetchall()
        conn.close()
        return {k: v for k, v in rows}

    def set_config(self, key: str, value: str):
        conn = sqlite3.connect(self.path)
        cur = conn.cursor()
        cur.execute(
            "REPLACE INTO config (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (key, value),
        )
        conn.commit()
        conn.close()

    # ─── Alerts ──────────────────────────────────────────────────

    def get_all_alerts(self) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "SELECT id, alert_type, title, description, scheduled_at, metadata, created_at "
            "FROM alerts WHERE is_active = 1 ORDER BY scheduled_at ASC, created_at DESC"
        )
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    def create_alert(self, alert_type: str, title: str, description: str = None,
                     scheduled_at: str = None, metadata: str = None) -> int:
        conn = sqlite3.connect(self.path)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO alerts (alert_type, title, description, scheduled_at, metadata) "
            "VALUES (?, ?, ?, ?, ?)",
            (alert_type, title, description, scheduled_at, metadata),
        )
        conn.commit()
        alert_id = cur.lastrowid
        conn.close()
        return alert_id

    def dismiss_alert(self, alert_id: int):
        conn = sqlite3.connect(self.path)
        cur = conn.cursor()
        cur.execute("UPDATE alerts SET is_active = 0 WHERE id = ?", (alert_id,))
        conn.commit()
        conn.close()
import sqlite3

class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        """Hilfsmethode für sauberes Connection-Management und Foreign Keys."""
        conn = sqlite3.connect(self.db_path)
        # automatic delete of associated data as per architecture definition (CASCADE)
        conn.execute("PRAGMA foreign_keys = ON;")
        # return rows as dicts
        conn.row_factory = sqlite3.Row 
        return conn

    def _init_db(self):
        """Initialisiert das Datenbankschema."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            
            # Identity (user's Tor-Address & Keys)
            cursor.execute('''CREATE TABLE IF NOT EXISTS identity (
                                id INTEGER PRIMARY KEY, 
                                onion_address TEXT,
                                key_type TEXT, 
                                private_key TEXT)''')
            
            # Contacts
            cursor.execute('''CREATE TABLE IF NOT EXISTS contact (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                alias TEXT NOT NULL,
                                onion_address TEXT UNIQUE NOT NULL)''')
            
            # Chats (1:1 Relation to contacs)
            cursor.execute('''CREATE TABLE IF NOT EXISTS chat (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                contact_id INTEGER NOT NULL,
                                FOREIGN KEY(contact_id) REFERENCES contact(id) ON DELETE CASCADE)''')
            
            # Messages
            cursor.execute('''CREATE TABLE IF NOT EXISTS message (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                chat_id INTEGER NOT NULL,
                                sender TEXT,
                                content TEXT NOT NULL,
                                timestamp TEXT NOT NULL,
                                status TEXT NOT NULL,
                                FOREIGN KEY(chat_id) REFERENCES chat(id) ON DELETE CASCADE)''')
            conn.commit()

    # ==========================================
    # IDENTITY METHODS
    # ==========================================
    def load_identity(self):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT onion_address, key_type, private_key FROM identity LIMIT 1")
            row = cursor.fetchone()
            return dict(row) if row else None

    def save_identity(self, onion_address, key_type, private_key):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM identity")
            cursor.execute("INSERT INTO identity (onion_address, key_type, private_key) VALUES (?, ?, ?)",
                           (onion_address, key_type, private_key))
            conn.commit()

    # ==========================================
    # CONTACT & CHAT METHODS
    # ==========================================
    def create_contact(self, alias, onion_address):
        """Erstellt einen Kontakt und automatisch den dazugehörigen Chat."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            try:
                # create contact
                cursor.execute("INSERT INTO contact (alias, onion_address) VALUES (?, ?)", (alias, onion_address))
                contact_id = cursor.lastrowid
                
                # create chat for contact_id
                cursor.execute("INSERT INTO chat (contact_id) VALUES (?)", (contact_id,))
                chat_id = cursor.lastrowid
                conn.commit()
                return contact_id, chat_id
            except sqlite3.IntegrityError:
                # if onion_address already exists
                return None, None

    def delete_contact(self, contact_id):
        """Löscht einen Kontakt (löscht via CASCADE auch Chat und Messages)."""
        with self._get_conn() as conn:
            conn.execute("DELETE FROM contact WHERE id = ?", (contact_id,))
            conn.commit()

    def update_alias(self, contact_id, new_alias):
        with self._get_conn() as conn:
            conn.execute("UPDATE contact SET alias = ? WHERE id = ?", (new_alias, contact_id))
            conn.commit()

    def get_onion_for_chat(self, chat_id):
        """Holt die Ziel-Onion-Adresse für einen bestimmten Chat (fürs Senden)."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('''SELECT c.onion_address FROM contact c
                              JOIN chat ch ON c.id = ch.contact_id
                              WHERE ch.id = ?''', (chat_id,))
            row = cursor.fetchone()
            return row['onion_address'] if row else None

    def get_chat_id_by_onion(self, onion_address):
        """Sucht den passenden Chat zu einer eingehenden Onion-Adresse."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('''SELECT ch.id FROM chat ch
                              JOIN contact c ON ch.contact_id = c.id
                              WHERE c.onion_address = ?''', (onion_address,))
            row = cursor.fetchone()
            return row['id'] if row else None

    # ==========================================
    # MESSAGE METHODS
    # ==========================================
    def save_message(self, chat_id, content, timestamp, status, sender):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO message (chat_id, sender, content, timestamp, status) 
                              VALUES (?, ?, ?, ?, ?)''', 
                           (chat_id, sender, content, timestamp, status))
            conn.commit()
            return cursor.lastrowid

    def get_messages_for_chat(self, chat_id):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id as message_id, content, timestamp, sender, status FROM message WHERE chat_id = ?", (chat_id,))
            return [dict(row) for row in cursor.fetchall()]

    def delete_message(self, message_id, chat_id):
        with self._get_conn() as conn:
            conn.execute("DELETE FROM message WHERE id = ? AND chat_id = ?", (message_id, chat_id))
            conn.commit()

    def clear_chat_history(self, chat_id):
        with self._get_conn() as conn:
            conn.execute("DELETE FROM message WHERE chat_id = ?", (chat_id,))
            conn.commit()

    def get_all_chats_with_last_message(self):
        """Zieht alle Chats, kombiniert mit Kontakt-Infos und der jeweils letzten Nachricht."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            # use subselect to get most recent message per chat
            query = '''
                SELECT 
                    ch.id as chat_id, 
                    c.id as contact_id, 
                    c.alias,
                    m.content, 
                    m.timestamp, 
                    m.status
                FROM chat ch
                JOIN contact c ON ch.contact_id = c.id
                LEFT JOIN message m ON m.id = (
                    SELECT id FROM message 
                    WHERE chat_id = ch.id 
                    ORDER BY id DESC LIMIT 1
                )
            '''
            cursor.execute(query)
            
            results = []
            for row in cursor.fetchall():
                chat_obj = {
                    "chat_id": row['chat_id'],
                    "alias": row['alias'],
                    "contact_id": row['contact_id'],
                }
                # if messages already exist, then attach last_message
                if row['content'] is not None:
                    chat_obj["last_message"] = {
                        "content": row['content'],
                        "timestamp": row['timestamp'],
                        "status": row['status']
                    }
                else:
                    chat_obj["last_message"] = None
                    
                results.append(chat_obj)
                
            return results
import sqlite3
import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

DB_PATH = os.path.join(os.path.dirname(__file__), 'chat_system.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT UNIQUE NOT NULL,
            name TEXT,
            user_type TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT UNIQUE NOT NULL,
            visitor_id TEXT NOT NULL,
            agent_id TEXT,
            status TEXT DEFAULT 'waiting',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            sender_id TEXT NOT NULL,
            sender_type TEXT NOT NULL,
            message_type TEXT DEFAULT 'text',
            content TEXT NOT NULL,
            file_name TEXT,
            file_path TEXT,
            file_size INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_messages_conversation 
        ON messages(conversation_id)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_conversations_visitor 
        ON conversations(visitor_id)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_conversations_agent 
        ON conversations(agent_id)
    ''')
    
    conn.commit()
    conn.close()

class User:
    def __init__(self, user_id: str, name: str, user_type: str, display_id: int = 0):
        self.user_id = user_id
        self.name = name
        self.user_type = user_type
        self.display_id = display_id
    
    @classmethod
    def create(cls, user_id: str, name: str, user_type: str) -> 'User':
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO users (user_id, name, user_type) 
                VALUES (?, ?, ?)
            ''', (user_id, name, user_type))
            conn.commit()
            display_id = cursor.lastrowid
            conn.close()
            return cls(user_id, name, user_type, display_id)
        except sqlite3.IntegrityError:
            cursor.execute('''
                UPDATE users SET name = ?, last_active = CURRENT_TIMESTAMP 
                WHERE user_id = ?
            ''', (name, user_id))
            conn.commit()
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            conn.close()
            if row:
                return cls(row['user_id'], row['name'], row['user_type'], row['id'])
            return cls(user_id, name, user_type, 0)
    
    @classmethod
    def get(cls, user_id: str) -> Optional['User']:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return cls(row['user_id'], row['name'], row['user_type'], row['id'])
        return None
    
    def update_last_active(self):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE user_id = ?
        ''', (self.user_id,))
        conn.commit()
        conn.close()

class Conversation:
    def __init__(self, conversation_id: str, visitor_id: str, agent_id: Optional[str] = None, 
                 status: str = 'waiting', created_at: Optional[str] = None):
        self.conversation_id = conversation_id
        self.visitor_id = visitor_id
        self.agent_id = agent_id
        self.status = status
        self.created_at = created_at
    
    @classmethod
    def create(cls, visitor_id: str) -> 'Conversation':
        import uuid
        conversation_id = str(uuid.uuid4())
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO conversations (conversation_id, visitor_id, status)
            VALUES (?, ?, 'waiting')
        ''', (conversation_id, visitor_id))
        conn.commit()
        conn.close()
        return cls(conversation_id, visitor_id)
    
    @classmethod
    def get(cls, conversation_id: str) -> Optional['Conversation']:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM conversations WHERE conversation_id = ?', (conversation_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return cls(
                row['conversation_id'], 
                row['visitor_id'], 
                row['agent_id'],
                row['status'],
                row['created_at']
            )
        return None
    
    @classmethod
    def get_waiting(cls) -> List['Conversation']:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM conversations 
            WHERE status = 'waiting' 
            ORDER BY created_at ASC
        ''')
        rows = cursor.fetchall()
        conn.close()
        return [cls(r['conversation_id'], r['visitor_id'], r['agent_id'], r['status'], r['created_at']) 
                for r in rows]
    
    @classmethod
    def get_active_for_agent(cls, agent_id: str) -> List['Conversation']:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM conversations 
            WHERE agent_id = ? AND status = 'active'
            ORDER BY updated_at DESC
        ''', (agent_id,))
        rows = cursor.fetchall()
        conn.close()
        return [cls(r['conversation_id'], r['visitor_id'], r['agent_id'], r['status'], r['created_at']) 
                for r in rows]
    
    @classmethod
    def get_by_visitor(cls, visitor_id: str) -> Optional['Conversation']:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM conversations 
            WHERE visitor_id = ? AND status IN ('waiting', 'active')
            ORDER BY created_at DESC
            LIMIT 1
        ''', (visitor_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return cls(
                row['conversation_id'], 
                row['visitor_id'], 
                row['agent_id'],
                row['status'],
                row['created_at']
            )
        return None
    
    def assign_agent(self, agent_id: str) -> bool:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE conversations 
            SET agent_id = ?, status = 'active', updated_at = CURRENT_TIMESTAMP
            WHERE conversation_id = ? AND status = 'waiting' AND agent_id IS NULL
        ''', (agent_id, self.conversation_id))
        affected_rows = cursor.rowcount
        conn.commit()
        
        if affected_rows > 0:
            self.agent_id = agent_id
            self.status = 'active'
            conn.close()
            return True
        else:
            cursor.execute('SELECT * FROM conversations WHERE conversation_id = ?', (self.conversation_id,))
            row = cursor.fetchone()
            conn.close()
            if row:
                self.agent_id = row['agent_id']
                self.status = row['status']
            return False
    
    def close(self):
        self.status = 'closed'
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE conversations 
            SET status = 'closed', updated_at = CURRENT_TIMESTAMP
            WHERE conversation_id = ?
        ''', (self.conversation_id,))
        conn.commit()
        conn.close()

class Message:
    def __init__(self, conversation_id: str, sender_id: str, sender_type: str, 
                 content: str, message_type: str = 'text',
                 file_name: Optional[str] = None, file_path: Optional[str] = None, 
                 file_size: Optional[int] = None, created_at: Optional[str] = None):
        self.conversation_id = conversation_id
        self.sender_id = sender_id
        self.sender_type = sender_type
        self.content = content
        self.message_type = message_type
        self.file_name = file_name
        self.file_path = file_path
        self.file_size = file_size
        self.created_at = created_at
    
    @classmethod
    def create(cls, conversation_id: str, sender_id: str, sender_type: str, 
               content: str, message_type: str = 'text',
               file_name: Optional[str] = None, file_path: Optional[str] = None, 
               file_size: Optional[int] = None) -> 'Message':
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO messages 
            (conversation_id, sender_id, sender_type, message_type, content, 
             file_name, file_path, file_size)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (conversation_id, sender_id, sender_type, message_type, content, 
              file_name, file_path, file_size))
        
        cursor.execute('''
            UPDATE conversations 
            SET updated_at = CURRENT_TIMESTAMP
            WHERE conversation_id = ?
        ''', (conversation_id,))
        
        conn.commit()
        conn.close()
        return cls(conversation_id, sender_id, sender_type, content, message_type,
                   file_name, file_path, file_size)
    
    @classmethod
    def get_by_conversation(cls, conversation_id: str, limit: int = 100) -> List['Message']:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM messages 
            WHERE conversation_id = ? 
            ORDER BY created_at ASC
            LIMIT ?
        ''', (conversation_id, limit))
        rows = cursor.fetchall()
        conn.close()
        return [cls(
            r['conversation_id'], r['sender_id'], r['sender_type'],
            r['content'], r['message_type'],
            r['file_name'], r['file_path'], r['file_size'], r['created_at']
        ) for r in rows]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'conversation_id': self.conversation_id,
            'sender_id': self.sender_id,
            'sender_type': self.sender_type,
            'content': self.content,
            'message_type': self.message_type,
            'file_name': self.file_name,
            'file_size': self.file_size,
            'created_at': self.created_at
        }

init_db()

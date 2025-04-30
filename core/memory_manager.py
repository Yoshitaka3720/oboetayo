# memory_manager.py

import threading
import sqlite3
import time
import math

class MemoryManager:
    def __init__(self, db_path="memory.db"):
        self.lock = threading.Lock()
        # allow access from multiple threads
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        # use WAL mode for better concurrency
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self._init_db()

    def _init_db(self):
        with self.lock:
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message TEXT,
                    timestamp REAL,
                    strength REAL
                )
            ''')
            self.conn.commit()

    def _execute(self, sql, params=(), commit=False):
        with self.lock:
            cur = self.conn.execute(sql, params)
            if commit:
                self.conn.commit()
            return cur

    def add(self, message, timestamp=None, strength=1.0):
        if timestamp is None:
            timestamp = time.time()
        # check if message exists
        cur = self._execute("SELECT id, strength FROM memories WHERE message = ?", (message,))
        row = cur.fetchone()
        if row:
            mem_id, current_strength = row
            new_strength = min(current_strength + 0.1, 1.0)
            self._execute(
                "UPDATE memories SET strength = ? WHERE id = ?", (new_strength, mem_id), commit=True
            )
        else:
            self._execute(
                "INSERT INTO memories (message, timestamp, strength) VALUES (?, ?, ?)",
                (message, timestamp, strength), commit=True
            )

    def decay(self):
        now = time.time()
        cur = self._execute("SELECT id, timestamp, strength FROM memories")
        rows = cur.fetchall()
        for mem_id, timestamp, strength in rows:
            # simple half-life decay: half per 24h
            hours = (now - timestamp) / 3600
            decay_factor = 0.5 ** (hours / 24)
            new_strength = strength * decay_factor
            self._execute(
                "UPDATE memories SET strength = ? WHERE id = ?", (new_strength, mem_id), commit=True
            )

    def get_all(self):
        cur = self._execute(
            "SELECT message, strength FROM memories ORDER BY id DESC"
        )
        return cur.fetchall()
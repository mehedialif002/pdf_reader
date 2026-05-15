import sqlite3
import json
import re
from datetime import datetime
from typing import List, Dict


class EditLearner:

    def __init__(self, db_path: str = "./edits.db"):
        self.db_path = db_path
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS edits (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                original   TEXT,
                edited     TEXT,
                doc_id     TEXT,
                draft_type TEXT,
                patterns   TEXT,
                created_at TEXT
            )
        """)
        conn.commit()
        conn.close()

    def save_edit(self, original: str, edited: str,
                  doc_id: str = None, draft_type: str = None) -> Dict:

        patterns = self._extract_patterns(original, edited)

        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO edits VALUES (NULL,?,?,?,?,?,?)",
            (original, edited, doc_id, draft_type,
             json.dumps(patterns), datetime.now().isoformat())
        )
        conn.commit()
        conn.close()

        return {"patterns": patterns, "message": "Edit saved"}

    def get_preferences(self, draft_type: str = None, limit: int = 10) -> List[str]:
        conn    = sqlite3.connect(self.db_path)
        cursor  = conn.execute(
            "SELECT patterns FROM edits ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )
        all_patterns = []
        for row in cursor.fetchall():
            all_patterns.extend(json.loads(row[0]))
        conn.close()

        # Most common patterns আগে রাখো
        counts = {}
        for p in all_patterns:
            counts[p] = counts.get(p, 0) + 1
        return sorted(counts.keys(), key=lambda x: counts[x], reverse=True)[:8]

    def get_stats(self) -> Dict:
        conn  = sqlite3.connect(self.db_path)
        total = conn.execute("SELECT COUNT(*) FROM edits").fetchone()[0]
        conn.close()
        return {"total_edits": total, "preferences": self.get_preferences()}

    def get_history(self, limit: int = 20) -> List[Dict]:
        conn   = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT id, doc_id, draft_type, patterns, created_at FROM edits "
            "ORDER BY created_at DESC LIMIT ?", (limit,)
        )
        rows = cursor.fetchall()
        conn.close()
        return [
            {"id": r[0], "doc_id": r[1], "draft_type": r[2],
             "patterns": json.loads(r[3]), "created_at": r[4]}
            for r in rows
        ]

    def _extract_patterns(self, original: str, edited: str) -> List[str]:
        orig_set   = set(original.split("\n"))
        edited_set = set(edited.split("\n"))
        added      = edited_set - orig_set
        removed    = orig_set - edited_set
        patterns   = []

        if len(edited) > len(original):
            patterns.append("Operator prefers detailed explanations")
        else:
            patterns.append("Operator prefers concise summaries")

        for line in added:
            if re.match(r"^\d+\.", line.strip()):
                patterns.append("Operator prefers numbered lists")
            if line.strip().isupper():
                patterns.append("Operator uses uppercase section headers")

        for line in removed:
            if "NOT IN DOCUMENTS" in line.upper():
                patterns.append("Operator removes unsupported placeholder text")

        return list(set(patterns))
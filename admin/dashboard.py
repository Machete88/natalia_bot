"""Minimal Admin-Dashboard: zeigt Statistiken als einfache HTML-Seite.

Starten mit: python -m admin.dashboard
Oeffnet: http://localhost:8080

Nur lokal verfuegbar - kein Passwort noetig da localhost only.
"""
from __future__ import annotations

import json
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


def _get_stats(db_path: str) -> dict:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        users = conn.execute("SELECT COUNT(*) as cnt FROM users").fetchone()["cnt"]
        total_vocab = conn.execute("SELECT COUNT(*) as cnt FROM vocab_items").fetchone()["cnt"]
        mastered = conn.execute(
            "SELECT COUNT(*) as cnt FROM vocab_progress WHERE status='mastered'"
        ).fetchone()["cnt"]
        learning = conn.execute(
            "SELECT COUNT(*) as cnt FROM vocab_progress WHERE status='learning'"
        ).fetchone()["cnt"]
        hw_count = conn.execute(
            "SELECT COUNT(*) as cnt FROM homework_submissions"
        ).fetchone()["cnt"]
        streaks = conn.execute(
            "SELECT u.name, s.current_streak, s.longest_streak "
            "FROM streaks s JOIN users u ON s.user_id=u.id ORDER BY s.current_streak DESC"
        ).fetchall()
        recent_hw = conn.execute(
            "SELECT hs.created_at, hs.extracted_text, u.name "
            "FROM homework_submissions hs JOIN users u ON hs.user_id=u.id "
            "ORDER BY hs.created_at DESC LIMIT 5"
        ).fetchall()
        vocab_list = conn.execute(
            "SELECT vi.word_de, vi.word_ru, vi.level, vi.topic, "
            "COUNT(vp.id) as attempts, "
            "SUM(CASE WHEN vp.status='mastered' THEN 1 ELSE 0 END) as mastered_count "
            "FROM vocab_items vi "
            "LEFT JOIN vocab_progress vp ON vi.id=vp.vocab_id "
            "GROUP BY vi.id ORDER BY vi.level, vi.topic"
        ).fetchall()

    return {
        "users": users,
        "total_vocab": total_vocab,
        "mastered": mastered,
        "learning": learning,
        "hw_count": hw_count,
        "streaks": [dict(r) for r in streaks],
        "recent_hw": [dict(r) for r in recent_hw],
        "vocab_list": [dict(r) for r in vocab_list],
    }


def _build_html(stats: dict) -> str:
    streak_rows = "".join(
        f"<tr><td>{r['name']}</td><td>\U0001f525 {r['current_streak']}</td><td>{r['longest_streak']}</td></tr>"
        for r in stats["streaks"]
    )
    hw_rows = "".join(
        f"<tr><td>{r['created_at'][:16]}</td><td>{r['name']}</td>"
        f"<td style='max-width:400px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap'>{(r['extracted_text'] or '')[:120]}</td></tr>"
        for r in stats["recent_hw"]
    )
    vocab_rows = "".join(
        f"<tr><td>{r['level']}</td><td>{r['topic']}</td>"
        f"<td><b>{r['word_de']}</b></td><td>{r['word_ru']}</td>"
        f"<td>{r['attempts']}</td><td>{'\u2705' if r['mastered_count'] else ''}</td></tr>"
        for r in stats["vocab_list"]
    )

    return f"""
<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>Natalia Bot — Admin Dashboard</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: system-ui, sans-serif; background: #f5f4f0; color: #1a1a1a; padding: 2rem; }}
  h1 {{ font-size: 1.6rem; margin-bottom: 1.5rem; color: #01696f; }}
  h2 {{ font-size: 1.1rem; margin: 1.5rem 0 0.5rem; color: #333; }}
  .kpis {{ display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 1.5rem; }}
  .kpi {{ background: #fff; border-radius: 10px; padding: 1rem 1.5rem; min-width: 140px;
           box-shadow: 0 2px 8px rgba(0,0,0,.07); }}
  .kpi-val {{ font-size: 2rem; font-weight: 700; color: #01696f; }}
  .kpi-lbl {{ font-size: 0.8rem; color: #666; margin-top: 0.2rem; }}
  table {{ width: 100%; border-collapse: collapse; background: #fff;
           border-radius: 10px; overflow: hidden;
           box-shadow: 0 2px 8px rgba(0,0,0,.07); margin-bottom: 1.5rem; }}
  th {{ background: #01696f; color: #fff; padding: 0.6rem 0.8rem; text-align: left; font-size: 0.85rem; }}
  td {{ padding: 0.5rem 0.8rem; border-bottom: 1px solid #eee; font-size: 0.9rem; }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: #f0faf9; }}
  footer {{ margin-top: 2rem; font-size: 0.75rem; color: #999; text-align: center; }}
</style>
</head>
<body>
<h1>\U0001f916 Natalia Bot — Admin Dashboard</h1>

<div class="kpis">
  <div class="kpi"><div class="kpi-val">{stats['users']}</div><div class="kpi-lbl">Nutzer</div></div>
  <div class="kpi"><div class="kpi-val">{stats['total_vocab']}</div><div class="kpi-lbl">Vokabeln gesamt</div></div>
  <div class="kpi"><div class="kpi-val">{stats['mastered']}</div><div class="kpi-lbl">Gemeistert \U0001f3c6</div></div>
  <div class="kpi"><div class="kpi-val">{stats['learning']}</div><div class="kpi-lbl">In Arbeit \U0001f504</div></div>
  <div class="kpi"><div class="kpi-val">{stats['hw_count']}</div><div class="kpi-lbl">Hausaufgaben</div></div>
</div>

<h2>\U0001f525 Streaks</h2>
<table>
  <thead><tr><th>Name</th><th>Aktuell</th><th>Rekord</th></tr></thead>
  <tbody>{streak_rows if streak_rows else '<tr><td colspan=3 style="color:#999">Noch keine Daten</td></tr>'}</tbody>
</table>

<h2>\U0001f4f8 Letzte Hausaufgaben</h2>
<table>
  <thead><tr><th>Datum</th><th>Name</th><th>Erkannter Text (Vorschau)</th></tr></thead>
  <tbody>{hw_rows if hw_rows else '<tr><td colspan=3 style="color:#999">Keine Einreichungen</td></tr>'}</tbody>
</table>

<h2>\U0001f4da Vokabeln</h2>
<table>
  <thead><tr><th>Level</th><th>Topic</th><th>Deutsch</th><th>Russisch</th><th>Versuche</th><th>Gemeistert</th></tr></thead>
  <tbody>{vocab_rows}</tbody>
</table>

<footer>Natalia Bot Admin — nur lokal verf\u00fcgbar • <a href="javascript:location.reload()">Aktualisieren</a></footer>
</body>
</html>
"""


class DashboardHandler(BaseHTTPRequestHandler):
    db_path: str = "natalia.db"

    def log_message(self, format, *args):
        pass  # Kein Apache-Log

    def do_GET(self):
        if self.path not in ("/", "/index.html"):
            self.send_response(404)
            self.end_headers()
            return
        try:
            stats = _get_stats(self.db_path)
            html = _build_html(stats)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Error: {e}".encode())


def run_dashboard(db_path: str = "natalia.db", port: int = 8080) -> None:
    DashboardHandler.db_path = db_path
    server = HTTPServer(("127.0.0.1", port), DashboardHandler)
    print(f"\U0001f4ca Admin Dashboard: http://localhost:{port}")
    server.serve_forever()


if __name__ == "__main__":
    import sys
    from pathlib import Path
    db = sys.argv[1] if len(sys.argv) > 1 else "natalia.db"
    run_dashboard(db_path=db)

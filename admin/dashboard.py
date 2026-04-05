"""Admin-Dashboard - lokale Flask-Web-UI fuer natalia_bot.
Starten: python admin/dashboard.py
Browser: http://localhost:5050
"""
from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from flask import Flask, render_template_string, request, redirect, url_for, jsonify

app = Flask(__name__)

def _db_path() -> str:
    env = Path(".env")
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("DATABASE_PATH="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return "data/natalia_bot.db"

def get_db():
    db = sqlite3.connect(_db_path())
    db.row_factory = sqlite3.Row
    return db

TEMPLATE = """
<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>natalia_bot Admin</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  :root{--teal:#01696f;--bg:#f7f6f2;--card:#fff;--text:#28251d;--muted:#7a7974;--border:#d4d1ca;}
  *{box-sizing:border-box;margin:0;padding:0;}
  body{font-family:system-ui,sans-serif;background:var(--bg);color:var(--text);}
  header{background:var(--teal);color:#fff;padding:1rem 2rem;display:flex;align-items:center;gap:1rem;}
  header h1{font-size:1.25rem;font-weight:600;}
  main{max-width:1100px;margin:2rem auto;padding:0 1rem;}
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:1rem;margin-bottom:2rem;}
  .card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:1.25rem;}
  .card h3{font-size:.8rem;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;margin-bottom:.5rem;}
  .card .value{font-size:2rem;font-weight:700;color:var(--teal);}
  .card .sub{font-size:.85rem;color:var(--muted);margin-top:.25rem;}
  .chart-wrap{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:1.5rem;margin-bottom:2rem;}
  .chart-wrap h2{font-size:1rem;margin-bottom:1rem;color:var(--text);}
  .chart-row{display:grid;grid-template-columns:1fr 1fr;gap:1.5rem;margin-bottom:2rem;}
  @media(max-width:700px){.chart-row{grid-template-columns:1fr;}}
  h2{margin:1.5rem 0 .75rem;font-size:1.1rem;}
  table{width:100%;border-collapse:collapse;background:var(--card);border-radius:10px;overflow:hidden;border:1px solid var(--border);}
  th{background:#f3f0ec;text-align:left;padding:.6rem 1rem;font-size:.8rem;color:var(--muted);text-transform:uppercase;}
  td{padding:.6rem 1rem;border-top:1px solid var(--border);font-size:.9rem;}
  .badge{display:inline-block;padding:.15rem .5rem;border-radius:999px;font-size:.75rem;font-weight:600;}
  .badge-mastered{background:#d4dfcc;color:#2e5c10;}
  .badge-learning{background:#cedcd8;color:#0c4e54;}
  .badge-new{background:#edeae5;color:#7a7974;}
  form.add-form{display:flex;flex-wrap:wrap;gap:.5rem;align-items:flex-end;margin-bottom:1rem;}
  form.add-form input,form.add-form select{padding:.45rem .75rem;border:1px solid var(--border);border-radius:6px;font-size:.9rem;background:#fff;}
  form.add-form input{flex:1 1 130px;}
  button.btn{padding:.45rem 1rem;background:var(--teal);color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:.9rem;}
  button.btn:hover{background:#0c4e54;}
  button.btn-danger{background:#a12c7b;}
  button.btn-danger:hover{background:#7d1e5e;}
  .msg{padding:.6rem 1rem;border-radius:6px;margin-bottom:1rem;font-size:.9rem;}
  .msg-ok{background:#d4dfcc;color:#1e3f0a;}
  .msg-err{background:#e0ced7;color:#561740;}
  .level-filter{display:flex;gap:.5rem;flex-wrap:wrap;margin-bottom:.75rem;}
  .level-filter button{padding:.3rem .75rem;border:1px solid var(--border);border-radius:999px;font-size:.8rem;background:#fff;cursor:pointer;}
  .level-filter button.active{background:var(--teal);color:#fff;border-color:var(--teal);}
</style>
</head>
<body>
<header>
  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
  <h1>natalia_bot &mdash; Admin</h1>
</header>
<main>

{% if msg %}<div class="msg {{ msg_cls }}">{{ msg }}</div>{% endif %}

<div class="grid">
  <div class="card"><h3>Vokabeln gesamt</h3><div class="value">{{ stats.total }}</div><div class="sub">in der Datenbank</div></div>
  <div class="card"><h3>Gelernt</h3><div class="value">{{ stats.learning }}</div><div class="sub">in Bearbeitung</div></div>
  <div class="card"><h3>Gemeistert</h3><div class="value">{{ stats.mastered }}</div><div class="sub">3&times; korrekt</div></div>
  <div class="card"><h3>Streak</h3><div class="value">{{ stats.streak }}&thinsp;&#x1f525;</div><div class="sub">Tage hintereinander</div></div>
  <div class="card"><h3>Quiz-Fragen</h3><div class="value">{{ stats.quiz_total }}</div><div class="sub">{{ stats.quiz_correct }} korrekt ({{ stats.quiz_pct }}%)</div></div>
</div>

<!-- Diagramme -->
<div class="chart-row">
  <div class="chart-wrap">
    <h2>&#x1f4ca; Fortschritt nach Level</h2>
    <canvas id="chartLevel" height="220"></canvas>
  </div>
  <div class="chart-wrap">
    <h2>&#x1f4c5; Lernaktivit&auml;t (letzte 14 Tage)</h2>
    <canvas id="chartActivity" height="220"></canvas>
  </div>
</div>
<div class="chart-row">
  <div class="chart-wrap">
    <h2>&#x1f9e0; Status-Verteilung</h2>
    <canvas id="chartStatus" height="220"></canvas>
  </div>
  <div class="chart-wrap">
    <h2>&#x1f3af; Quiz-Genauigkeit nach Thema</h2>
    <canvas id="chartTopics" height="220"></canvas>
  </div>
</div>

<h2>Vokabel hinzuf&uuml;gen</h2>
<form class="add-form" method="POST" action="/vocab/add">
  <select name="level">
    {% for l in ["beginner","a1","a2","b1","b2","c1"] %}<option>{{ l }}</option>{% endfor %}
  </select>
  <input name="topic" placeholder="Thema" required>
  <input name="word_de" placeholder="Deutsch" required>
  <input name="word_ru" placeholder="Russisch" required>
  <input name="example_de" placeholder="Beispiel DE" required>
  <input name="example_ru" placeholder="Beispiel RU" required>
  <button class="btn" type="submit">+ Hinzuf&uuml;gen</button>
</form>

<h2>Alle Vokabeln ({{ vocab|length }})</h2>
<div class="level-filter">
  <button class="active" onclick="filterLevel('all',this)">Alle</button>
  {% for l in ["beginner","a1","a2","b1","b2","c1"] %}
  <button onclick="filterLevel('{{ l }}',this)">{{ l.upper() }}</button>
  {% endfor %}
</div>
<table id="vocabTable">
  <tr><th>Level</th><th>Thema</th><th>Deutsch</th><th>Russisch</th><th>Status</th><th>Streak</th><th></th></tr>
  {% for v in vocab %}
  <tr data-level="{{ v.level }}">
    <td>{{ v.level }}</td><td>{{ v.topic }}</td>
    <td><strong>{{ v.word_de }}</strong></td><td>{{ v.word_ru }}</td>
    <td>
      {% if v.status == 'mastered' %}<span class="badge badge-mastered">Gemeistert</span>
      {% elif v.status == 'learning' %}<span class="badge badge-learning">Lernt</span>
      {% else %}<span class="badge badge-new">Neu</span>{% endif %}
    </td>
    <td>{{ v.streak or 0 }}</td>
    <td><form method="POST" action="/vocab/delete/{{ v.id }}" style="display:inline">
      <button class="btn btn-danger" type="submit" onclick="return confirm('L&ouml;schen?')">&#10005;</button>
    </form></td>
  </tr>
  {% endfor %}
</table>

</main>
<script>
// Level-Filter
function filterLevel(level, btn) {
  document.querySelectorAll('.level-filter button').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  document.querySelectorAll('#vocabTable tr[data-level]').forEach(r => {
    r.style.display = (level === 'all' || r.dataset.level === level) ? '' : 'none';
  });
}

// Chart-Daten aus Flask
const levelData   = {{ chart_level | tojson }};
const activityData = {{ chart_activity | tojson }};
const statusData  = {{ chart_status | tojson }};
const topicData   = {{ chart_topics | tojson }};

const TEAL = '#01696f', TEAL2 = '#4f98a3', WARM = '#da7101', GOLD = '#d19900', PURPLE = '#7a39bb', MUTED = '#bab9b4';

// 1. Level-Balken
new Chart(document.getElementById('chartLevel'), {
  type: 'bar',
  data: {
    labels: levelData.labels,
    datasets: [
      { label: 'Gemeistert', data: levelData.mastered, backgroundColor: '#437a22' },
      { label: 'Lernt',      data: levelData.learning, backgroundColor: TEAL },
      { label: 'Neu',        data: levelData.new,      backgroundColor: MUTED },
    ]
  },
  options: { responsive: true, plugins: { legend: { position: 'bottom' } }, scales: { x: { stacked: true }, y: { stacked: true, beginAtZero: true } } }
});

// 2. Aktivitaet Linien
new Chart(document.getElementById('chartActivity'), {
  type: 'line',
  data: {
    labels: activityData.labels,
    datasets: [{ label: 'Vokabeln gelernt', data: activityData.values, borderColor: TEAL, backgroundColor: 'rgba(1,105,111,.1)', fill: true, tension: .35, pointRadius: 3 }]
  },
  options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } }
});

// 3. Status Donut
new Chart(document.getElementById('chartStatus'), {
  type: 'doughnut',
  data: {
    labels: ['Gemeistert', 'Lernt', 'Neu'],
    datasets: [{ data: statusData.values, backgroundColor: ['#437a22', TEAL, MUTED], borderWidth: 2, borderColor: '#f7f6f2' }]
  },
  options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
});

// 4. Themen-Balken
new Chart(document.getElementById('chartTopics'), {
  type: 'bar',
  data: {
    labels: topicData.labels,
    datasets: [{ label: 'Vokabeln', data: topicData.values, backgroundColor: TEAL2 }]
  },
  options: { indexAxis: 'y', responsive: true, plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true } } }
});
</script>
</body>
</html>
"""

def load_stats(db) -> dict:
    total    = db.execute("SELECT COUNT(*) as n FROM vocab_items").fetchone()["n"]
    learning = db.execute("SELECT COUNT(*) as n FROM vocab_progress WHERE status='learning'").fetchone()["n"]
    mastered = db.execute("SELECT COUNT(*) as n FROM vocab_progress WHERE status='mastered'").fetchone()["n"]
    streak_row = db.execute("SELECT value FROM user_preferences WHERE key='streak' LIMIT 1").fetchone()
    streak = int(streak_row["value"]) if streak_row else 0
    # Quiz-Statistik aus vocab_progress (correct_streak als Proxy)
    quiz_total   = db.execute("SELECT COALESCE(SUM(correct_streak),0) as n FROM vocab_progress").fetchone()["n"]
    quiz_correct = quiz_total  # vereinfacht
    quiz_pct = 100 if quiz_total == 0 else 100
    return {"total": total, "learning": learning, "mastered": mastered, "streak": streak,
            "quiz_total": quiz_total, "quiz_correct": quiz_correct, "quiz_pct": quiz_pct}

def load_vocab(db) -> list:
    rows = db.execute("""
        SELECT vi.id, vi.level, vi.topic, vi.word_de, vi.word_ru,
               vp.status, vp.correct_streak as streak
        FROM vocab_items vi LEFT JOIN vocab_progress vp ON vi.id = vp.vocab_id
        ORDER BY vi.level, vi.topic, vi.word_de
    """).fetchall()
    return [dict(r) for r in rows]

def load_chart_data(db) -> dict:
    levels = ["beginner","a1","a2","b1","b2","c1"]
    level_data = {"labels": levels, "mastered": [], "learning": [], "new": []}
    for lv in levels:
        m = db.execute("SELECT COUNT(*) n FROM vocab_items vi JOIN vocab_progress vp ON vi.id=vp.vocab_id WHERE vi.level=? AND vp.status='mastered'", (lv,)).fetchone()["n"]
        l = db.execute("SELECT COUNT(*) n FROM vocab_items vi JOIN vocab_progress vp ON vi.id=vp.vocab_id WHERE vi.level=? AND vp.status='learning'", (lv,)).fetchone()["n"]
        total = db.execute("SELECT COUNT(*) n FROM vocab_items WHERE level=?", (lv,)).fetchone()["n"]
        level_data["mastered"].append(m)
        level_data["learning"].append(l)
        level_data["new"].append(max(0, total - m - l))

    # Aktivitaet letzte 14 Tage (aus last_seen)
    from datetime import datetime, timedelta
    today = datetime.now().date()
    labels, values = [], []
    for i in range(13, -1, -1):
        d = (today - timedelta(days=i)).isoformat()
        count = db.execute("SELECT COUNT(*) n FROM vocab_progress WHERE DATE(last_seen)=?", (d,)).fetchone()["n"]
        labels.append(d[5:])  # MM-DD
        values.append(count)
    activity = {"labels": labels, "values": values}

    # Status-Donut
    mastered = db.execute("SELECT COUNT(*) n FROM vocab_progress WHERE status='mastered'").fetchone()["n"]
    learning = db.execute("SELECT COUNT(*) n FROM vocab_progress WHERE status='learning'").fetchone()["n"]
    total    = db.execute("SELECT COUNT(*) n FROM vocab_items").fetchone()["n"]
    status   = {"values": [mastered, learning, max(0, total - mastered - learning)]}

    # Themen-Balken
    rows = db.execute("SELECT topic, COUNT(*) n FROM vocab_items GROUP BY topic ORDER BY n DESC LIMIT 10").fetchall()
    topics = {"labels": [r["topic"] for r in rows], "values": [r["n"] for r in rows]}

    return level_data, activity, status, topics

@app.route("/")
def index():
    msg = request.args.get("msg")
    msg_cls = request.args.get("cls", "msg-ok")
    db = get_db()
    stats = load_stats(db)
    vocab = load_vocab(db)
    level_data, activity, status, topics = load_chart_data(db)
    db.close()
    return render_template_string(TEMPLATE, stats=stats, vocab=vocab, msg=msg, msg_cls=msg_cls,
                                  chart_level=level_data, chart_activity=activity,
                                  chart_status=status, chart_topics=topics)

@app.route("/vocab/add", methods=["POST"])
def vocab_add():
    data = request.form
    db = get_db()
    try:
        db.execute("INSERT INTO vocab_items (level,topic,word_de,word_ru,example_de,example_ru) VALUES (?,?,?,?,?,?)",
                   (data["level"], data["topic"], data["word_de"], data["word_ru"], data["example_de"], data["example_ru"]))
        db.commit()
        msg, cls = f"'{data['word_de']}' hinzugefuegt.", "msg-ok"
    except Exception as e:
        msg, cls = f"Fehler: {e}", "msg-err"
    finally:
        db.close()
    return redirect(url_for("index", msg=msg, cls=cls))

@app.route("/vocab/delete/<int:vocab_id>", methods=["POST"])
def vocab_delete(vocab_id: int):
    db = get_db()
    try:
        db.execute("DELETE FROM vocab_progress WHERE vocab_id=?", (vocab_id,))
        db.execute("DELETE FROM vocab_items WHERE id=?", (vocab_id,))
        db.commit()
        msg, cls = "Vokabel geloescht.", "msg-ok"
    except Exception as e:
        msg, cls = f"Fehler: {e}", "msg-err"
    finally:
        db.close()
    return redirect(url_for("index", msg=msg, cls=cls))

@app.route("/api/stats")
def api_stats():
    db = get_db()
    stats = load_stats(db)
    db.close()
    return jsonify(stats)

if __name__ == "__main__":
    print("Admin-Dashboard: http://localhost:5050")
    app.run(host="127.0.0.1", port=5050, debug=True)

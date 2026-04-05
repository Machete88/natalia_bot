# Admin-Dashboard

Lokale Web-UI fuer natalia_bot.

## Starten

```powershell
# Einmalig Flask installieren (bereits in requirements.txt)
pip install flask

# Dashboard starten
python admin/dashboard.py
```

Dann im Browser: **http://localhost:5050**

## Funktionen

- **KPI-Kacheln**: Vokabeln gesamt, gelernt, gemeistert, Streak
- **Vokabel hinzufuegen**: Level, Thema, Deutsch, Russisch, Beispiele
- **Vokabeln loeschen**: Knopf in der Tabelle
- **Status-Anzeige**: Neu / Lernt / Gemeistert
- **REST API**: `GET /api/stats` liefert JSON

## Sicherheit

Das Dashboard laeuft nur lokal (127.0.0.1). Es ist nicht oeffentlich erreichbar.
Fuer Remote-Zugriff: SSH-Tunnel verwenden.

#!/bin/bash
SRC="/opt/natalia_bot"
DST="/opt/natalia_bot_backup_$(date +%Y%m%d_%H%M)"
cp -r "$SRC" "$DST" --exclude=".venv" --exclude="__pycache__"
echo "Backup: $DST"

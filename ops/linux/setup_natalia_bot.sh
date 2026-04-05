#!/bin/bash
set -e
INSTALL_DIR="/opt/natalia_bot"
echo "=== NataliaBot Linux Setup ==="

sudo apt-get update -q && sudo apt-get install -y -q python3.11 python3.11-venv python3-pip

if [ ! -d "$INSTALL_DIR" ]; then
    sudo mkdir -p "$INSTALL_DIR"
    sudo chown $USER:$USER "$INSTALL_DIR"
fi

cp -r . "$INSTALL_DIR/"
cd "$INSTALL_DIR"

python3.11 -m venv .venv
.venv/bin/pip install --upgrade pip --quiet
.venv/bin/pip install -r requirements.txt --quiet

for d in data logs media/audio media/cache media/stickers; do
    mkdir -p "$INSTALL_DIR/$d"
done

if [ ! -f "$INSTALL_DIR/.env" ]; then
    cp .env.example .env
    echo "[WICHTIG] Trage deine API-Keys in $INSTALL_DIR/.env ein!"
fi

sudo cp ops/linux/natalia-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable natalia-bot

echo "[OK] Setup abgeschlossen!"
echo "Starten: sudo systemctl start natalia-bot"

#!/bin/bash

source /app/venv/bin/activate

echo "[*] Start Tor Daemon in Background..."
tor -f /etc/tor/torrc &

echo "[*] Wait for Tor Bootstrapping cycle..."
sleep 5

echo "[*] Start Aether Python Backend..."

python /app/src/main.py
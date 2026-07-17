#!/bin/bash
echo "Beende alte Zombie-Broker..."
killall Python 2>/dev/null || true
echo "Starte Broker über das virtuelle Environment..."
.venv/bin/python -m broker

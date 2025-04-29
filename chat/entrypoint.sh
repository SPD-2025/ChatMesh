#!/bin/sh

# Extrai número do hostname (ex: peer_2 ➝ 2)
HOST=$(hostname)
NUM=$(echo $HOST | grep -o -E '[0-9]+')
export PEER_NAME="Peer-${NUM:-0}"

echo "Iniciando $PEER_NAME na porta $PORTA_RECEBIMENTO"

exec python chat.py

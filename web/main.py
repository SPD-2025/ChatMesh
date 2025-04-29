# web/main.py (atualizado para WebSocket, status, métricas)

from fastapi import FastAPI, Request, Form, WebSocket
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
import os
import socket
import aiofiles

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Configurações
LOGS_PATH = "/logs"
PEERS = {
    "Peer1": (os.getenv("PEER1_IP", "peer1"), int(os.getenv("PEER1_PORT", 5000))),
    "Peer2": (os.getenv("PEER2_IP", "peer2"), int(os.getenv("PEER2_PORT", 5001))),
}

# Função para testar se o peer está online
def testar_peer(ip, porta):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        s.connect((ip, porta))
        s.close()
        return True
    except:
        return False

# Função para contar mensagens
async def contar_mensagens():
    enviados = recebidos = 0
    if os.path.exists(LOGS_PATH):
        for filename in os.listdir(LOGS_PATH):
            if filename.endswith(".txt"):
                caminho = os.path.join(LOGS_PATH, filename)
                async with aiofiles.open(caminho, mode='r', encoding="utf-8") as f:
                    async for linha in f:
                        linha = linha.strip()
                        if "Mensagem enviada" in linha:
                            enviados += 1
                        elif "MENSAGEM RECEBIDA" in linha:
                            recebidos += 1
    return enviados, recebidos

@app.get("/")
async def index(request: Request, peer: str = None):
    mensagens = []
    status_peers = {nome: testar_peer(ip, porta) for nome, (ip, porta) in PEERS.items()}
    enviados, recebidos = await contar_mensagens()

    if os.path.exists(LOGS_PATH):
        for filename in os.listdir(LOGS_PATH):
            if filename.endswith(".txt"):
                peer_nome = filename.replace("_log.txt", "")
                if peer and peer_nome != peer:
                    continue
                caminho = os.path.join(LOGS_PATH, filename)
                async with aiofiles.open(caminho, mode='r', encoding="utf-8") as f:
                    async for linha in f:
                        mensagens.append((peer_nome, linha.strip()))
    mensagens.sort(key=lambda x: x[1])

    return templates.TemplateResponse("index.html", {
        "request": request,
        "mensagens": mensagens,
        "peer_filter": peer,
        "status_peers": status_peers,
        "enviados": enviados,
        "recebidos": recebidos,
    })

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        await websocket.send_text("refresh")
        await asyncio.sleep(5)

@app.post("/send")
async def send_message(mensagem: str = Form(...)):
    ip, porta = PEERS["Peer1"]
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((ip, porta))
        client_socket.sendall(mensagem.encode())
        client_socket.close()
    except Exception as e:
        print(f"Erro ao enviar mensagem: {e}")
    return RedirectResponse(url="/", status_code=303)

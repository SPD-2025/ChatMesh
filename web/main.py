from fastapi import FastAPI, Request, Form, WebSocket
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import os
import socket
import aiofiles
import asyncio
import time

app = FastAPI()
templates = Jinja2Templates(directory="templates")

LOGS_PATH = "/logs"
PEER_PORT = 5000

peers_cache = []
peers_last_update = 0

# Descobrir peers ativos
def descobrir_peers():
    global peers_cache, peers_last_update
    agora = time.time()
    if agora - peers_last_update < 30:  # só atualizar a cada 30 segundos
        return peers_cache
    vivos = []
    for i in range(2, 20):
        ip = f"172.18.0.{i}"
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            s.connect((ip, PEER_PORT))
            vivos.append(ip)
            s.close()
        except:
            continue
    peers_cache = vivos
    peers_last_update = agora
    return vivos

async def carregar_mensagens():
    mensagens = []
    if os.path.exists(LOGS_PATH):
        for arquivo in os.listdir(LOGS_PATH):
            if arquivo.endswith(".txt"):
                peer_nome = arquivo.replace("_log.txt", "")
                caminho = os.path.join(LOGS_PATH, arquivo)
                async with aiofiles.open(caminho, 'r') as f:
                    async for linha in f:
                        mensagens.append((peer_nome, linha.strip()))
    mensagens.sort(key=lambda x: x[1])
    return mensagens

@app.get("/")
async def index(request: Request):
    mensagens = await carregar_mensagens()
    peers_ativos = descobrir_peers()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "mensagens": mensagens,
        "peers_ativos": peers_ativos
    })

@app.get("/api/mensagens")
async def api_mensagens():
    mensagens = await carregar_mensagens()
    return JSONResponse(content=[{"peer": peer, "mensagem": msg} for peer, msg in mensagens])

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        await websocket.send_text("update")
        await asyncio.sleep(5)

@app.post("/send")
async def send_message(mensagem: str = Form(...)):
    peers = descobrir_peers()
    if not peers:
        print("Nenhum peer encontrado para envio!")
        return RedirectResponse(url="/", status_code=303)
    ip = peers[0]  # envia para o primeiro disponível
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((ip, PEER_PORT))
        client_socket.sendall(mensagem.encode())
        client_socket.close()
    except Exception as e:
        print(f"Erro ao enviar: {e}")
    return RedirectResponse(url="/", status_code=303)

# web/main.py

from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os
import socket
import aiofiles

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Configurações fixas
LOGS_PATH = "/logs"  # Volume compartilhado
PEER_DESTINO_IP = os.getenv("PEER_DESTINO_IP", "peer1")
PEER_DESTINO_PORTA = int(os.getenv("PEER_DESTINO_PORTA", 5000))

@app.get("/")
async def index(request: Request, peer: str = None):
    mensagens = []
    
    # Lê todos os arquivos de log
    if os.path.exists(LOGS_PATH):
        for filename in os.listdir(LOGS_PATH):
            if filename.endswith(".txt"):
                peer_nome = filename.replace("_log.txt", "")
                if peer and peer_nome != peer:
                    continue  # Aplica filtro
                caminho = os.path.join(LOGS_PATH, filename)
                async with aiofiles.open(caminho, mode='r', encoding="utf-8") as f:
                    async for linha in f:
                        mensagens.append((peer_nome, linha.strip()))
    mensagens.sort(key=lambda x: x[1])  # Ordena por timestamp simples

    return templates.TemplateResponse("index.html", {"request": request, "mensagens": mensagens, "peer_filter": peer})

@app.post("/send")
async def send_message(mensagem: str = Form(...)):
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((PEER_DESTINO_IP, PEER_DESTINO_PORTA))
        client_socket.sendall(mensagem.encode())
        client_socket.close()
    except Exception as e:
        print(f"Erro ao enviar mensagem: {e}")
    return RedirectResponse(url="/", status_code=303)

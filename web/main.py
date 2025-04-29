from fastapi import FastAPI, Request, Form, WebSocket
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import os
import socket
import aiofiles
import asyncio
import sqlite3
import time

app = FastAPI()
templates = Jinja2Templates(directory="templates")

LOGS_PATH = "/logs"
DB_PATH = os.path.join(LOGS_PATH, f"{os.getenv('PEER_NAME', 'Peer-Web')}.db")
PEER_DESTINO = os.getenv("PEER_DESTINO", "peer:5000")
FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", 8000))
NOME_WEB = os.getenv("PEER_NAME", "Peer-Web")

peers_cache = []
peers_last_update = 0

def inicializar_banco():
    os.makedirs(LOGS_PATH, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS mensagens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            remetente TEXT,
            conteudo TEXT
        )
    ''')
    conn.commit()
    conn.close()

async def carregar_mensagens():
    inicializar_banco()
    mensagens = []
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT remetente, conteudo FROM mensagens ORDER BY id')
    registros = cur.fetchall()
    conn.close()
    for remetente, conteudo in registros:
        mensagens.append({"peer": remetente, "conteudo": conteudo})
    return mensagens

@app.get("/")
async def index(request: Request):
    mensagens = await carregar_mensagens()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "mensagens": mensagens,
        "meu_peer": NOME_WEB
    })

@app.get("/api/mensagens")
async def api_mensagens():
    mensagens = await carregar_mensagens()
    return JSONResponse(content=mensagens)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        await websocket.send_text("update")
        await asyncio.sleep(5)

@app.post("/send")
async def send_message(mensagem: str = Form(...)):
    ip_port = PEER_DESTINO.split(":")
    ip = ip_port[0]
    port = int(ip_port[1])

    mensagem_formatada = f"{NOME_WEB}: {mensagem}"

    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((ip, port))
        client_socket.sendall(mensagem_formatada.encode())
        client_socket.close()
    except Exception as e:
        print(f"Erro enviando mensagem: {e}")

    return RedirectResponse(url="/", status_code=303)

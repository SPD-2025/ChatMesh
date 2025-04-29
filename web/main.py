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
    mensagens = []
    if not os.path.exists(LOGS_PATH):
        os.makedirs(LOGS_PATH, exist_ok=True)

    for arquivo in os.listdir(LOGS_PATH):
        if arquivo.endswith(".db"):
            caminho = os.path.join(LOGS_PATH, arquivo)
            conn = sqlite3.connect(caminho)
            cur = conn.cursor()
            try:
                cur.execute('SELECT remetente, conteudo FROM mensagens ORDER BY id')
                registros = cur.fetchall()
                for remetente, conteudo in registros:
                    mensagens.append({"peer": remetente, "conteudo": conteudo})
            except sqlite3.Error as e:
                print(f"Erro lendo {arquivo}: {e}")
            conn.close()

    # Remover duplicatas
    mensagens_unicas = []
    vistos = set()
    for msg in mensagens:
        chave = (msg["peer"], msg["conteudo"])
        if chave not in vistos:
            mensagens_unicas.append(msg)
            vistos.add(chave)

    return mensagens_unicas



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
        return JSONResponse(content={"status": "ok"})
    except Exception as e:
        print(f"Erro enviando mensagem: {e}")
        return JSONResponse(content={"status": "erro", "detalhes": str(e)}, status_code=500)
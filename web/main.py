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
PEER_PORT = 5000

hostname = socket.gethostname()
NOME_WEB = f"Peer-{hostname[:8]}"
DB_PATH = os.path.join(LOGS_PATH, f"{NOME_WEB}.db")

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


def descobrir_peers():
    global peers_cache, peers_last_update
    agora = time.time()
    if agora - peers_last_update < 30:
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

    # Remover duplicatas (mesma mensagem em múltiplos bancos)
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
    peers_ativos = descobrir_peers()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "mensagens": mensagens,
        "peers_ativos": peers_ativos,
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
    peers = descobrir_peers()
    if not peers:
        print("Nenhum peer encontrado!")
        return RedirectResponse(url="/", status_code=303)
    ip = peers[0]
    mensagem_formatada = f"{NOME_WEB}: {mensagem}"
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((ip, PEER_PORT))
        client_socket.sendall(mensagem_formatada.encode())
        client_socket.close()
    except Exception as e:
        print(f"Erro enviando: {e}")
    return RedirectResponse(url="/", status_code=303)

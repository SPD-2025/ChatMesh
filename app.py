# app.py com suporte a --webport para múltiplas interfaces web

import os
import socket
import sqlite3
import time
import argparse
import asyncio
from fastapi import FastAPI, WebSocket, Request, Form, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from multiprocessing import Process, Queue
import requests

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

connections = []
def servidor(db_path, port_queue):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))  # porta aleatória
    port = s.getsockname()[1]
    port_queue.put(port)
    s.listen()
    print(f"[SERVIDOR] Escutando na porta TCP {port}")
    while True:
        conn, _ = s.accept()
        p = Process(target=processar_cliente, args=(conn, db_path))
        p.daemon = True
        p.start()
def init_db(peer_name):
    os.makedirs("logs", exist_ok=True)
    db_path = f"logs/{peer_name}.db"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS mensagens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            remetente TEXT,
            conteudo TEXT
        )
    """)
    conn.commit()
    conn.close()
    return db_path

def salvar_mensagem(db_path, remetente, conteudo):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM mensagens WHERE remetente=? AND conteudo=?", (remetente, conteudo))
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO mensagens (timestamp, remetente, conteudo) VALUES (?, ?, ?)",
                    (time.strftime('%Y-%m-%d %H:%M:%S'), remetente, conteudo))
        conn.commit()
    conn.close()

def carregar_mensagens(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT timestamp, remetente, conteudo FROM mensagens ORDER BY timestamp")
    dados = cur.fetchall()
    conn.close()
    return [{"timestamp": ts, "peer": r, "conteudo": c} for ts, r, c in dados]

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "meu_peer": app.state.peer_name, "porta_tcp": app.state.port})

@app.get("/api/mensagens")
async def api_mensagens():
    return carregar_mensagens(app.state.db_path)

@app.post("/send")
async def send_message(mensagem: str = Form(...)):
    conteudo = mensagem.strip()
    if not conteudo:
        return JSONResponse(content={"erro": "mensagem vazia"}, status_code=400)

    salvar_mensagem(app.state.db_path, app.state.peer_name, conteudo)

    for peer_host, peer_port in app.state.peers:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((peer_host, peer_port))
            s.sendall(f"{app.state.peer_name}: {conteudo}".encode())
            s.close()
        except Exception as e:
            print(f"Erro enviando para {peer_host}:{peer_port} -> {e}")

    for ws in connections:
        try:
            await ws.send_text("update")
        except:
            pass
    return {"ok": True}
@app.get("/connect")
async def connect_peer(ip: str, port: int, callback: str = None, cbport: int = None):
    try:
        res = requests.get(f"http://{ip}:{port}/api/mensagens", timeout=5)
        mensagens = res.json()
        for m in mensagens:
            salvar_mensagem(app.state.db_path, m["peer"], m["conteudo"])
        for ws in connections:
            try:
                await ws.send_text("update")
            except:
                pass

        # reconectar de volta
        if callback and cbport:
            try:
                requests.get(f"http://{callback}:{cbport}/connect?ip=localhost&port={app.state.port}")
                print(f"[REVERSE] conectando de volta a {callback}:{cbport}")
            except Exception as e:
                print(f"[REVERSE] falhou ao conectar de volta: {e}")

        return {"status": f"Conectado a {ip}:{port} e sincronizado."}
    except Exception as e:
        return JSONResponse(content={"erro": str(e)}, status_code=500)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connections.append(websocket)
    await websocket.send_text(f"[status] conectado como {app.state.peer_name}:{app.state.port}")
    try:
        while True:
            await asyncio.sleep(60)
    except:
        connections.remove(websocket)

def processar_cliente(conn, db_path):
    try:
        data = conn.recv(4096).decode()
        if data:
            remetente, conteudo = data.split(": ", 1)
            salvar_mensagem(db_path, remetente, conteudo)
    except Exception as e:
        print(f"Erro ao receber: {e}")
    finally:
        conn.close()

def iniciar_socket_servidor(db_path):
    port_queue = Queue()
    p = Process(target=servidor, args=(db_path, port_queue))
    p.daemon = True
    p.start()
    app.state.port = port_queue.get()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True, help="Nome do peer")
    parser.add_argument("--peers", help="Lista de peers no formato IP:porta separados por vírgula")
    parser.add_argument("--webport", type=int, default=8000, help="Porta HTTP da interface web")
    args = parser.parse_args()

    app.state.peer_name = args.name
    app.state.peers = [tuple(p.split(":")) for p in args.peers.split(",")] if args.peers else []
    app.state.peers = [(h, int(p)) for h, p in app.state.peers]
    app.state.db_path = init_db(args.name)

    iniciar_socket_servidor(app.state.db_path)

    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=args.webport)

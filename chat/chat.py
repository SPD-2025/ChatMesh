import socket
import os
import time
import sqlite3
from multiprocessing import Process

# Nome único baseado no hostname do container
hostname = socket.gethostname()
NOME_PEER = os.getenv("PEER_NAME", socket.gethostname())
PORTA_RECEBIMENTO = int(os.getenv("PORTA_RECEBIMENTO", 5000))

LOG_DIR = "/logs"
DB_PATH = os.path.join(LOG_DIR, f"{NOME_PEER}.db")

# Controle de mensagens únicas
ultimas_mensagens = []
MAX_MENSAGENS = 100

peers_cache = []
peers_last_update = 0

def mensagem_ja_existe(remetente, conteudo):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
        SELECT COUNT(*) FROM mensagens
        WHERE remetente = ? AND conteudo = ?
    ''', (remetente, conteudo))
    count = cur.fetchone()[0]
    conn.close()
    return count > 0


def inicializar_banco():
    os.makedirs(LOG_DIR, exist_ok=True)
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

def salvar_mensagem(remetente, conteudo):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO mensagens (timestamp, remetente, conteudo)
        VALUES (?, ?, ?)
    ''', (time.strftime('%Y-%m-%d %H:%M:%S'), remetente, conteudo))
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
            s.connect((ip, PORTA_RECEBIMENTO))
            vivos.append(ip)
            s.close()
        except:
            continue
    peers_cache = vivos
    peers_last_update = agora
    return vivos

def replicar_para_outros_peers(mensagem, origem_ip):
    peers = descobrir_peers()
    for ip in peers:
        if ip != origem_ip:
            try:
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.connect((ip, PORTA_RECEBIMENTO))
                client_socket.sendall(f"[REPLICATED] {mensagem}".encode())
                client_socket.close()
                print(f"[{NOME_PEER}] Replicado para {ip}")
            except Exception as e:
                print(f"[{NOME_PEER}] Erro replicando para {ip}: {e}")

def servidor_receber():
    inicializar_banco()

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('', PORTA_RECEBIMENTO))
    server_socket.listen()
    print(f"[{NOME_PEER}] Servidor escutando na porta {PORTA_RECEBIMENTO}...")

    while True:
        conn, addr = server_socket.accept()
        data = conn.recv(1024)
        if data:
            mensagem = data.decode()
            is_replicated = mensagem.startswith("[REPLICATED] ")
            mensagem_pura = mensagem[12:] if is_replicated else mensagem

            remetente, conteudo = mensagem_pura.split(":", 1)
            remetente = remetente.strip()
            conteudo = conteudo.strip()

            if not mensagem_ja_existe(remetente, conteudo):
                salvar_mensagem(remetente, conteudo)

                if not is_replicated:
                    replicar_para_outros_peers(mensagem_pura, origem_ip=addr[0])
            else:
                print(f"[{NOME_PEER}] Mensagem duplicada detectada no banco, ignorando.")

        conn.close()

if __name__ == "__main__":
    servidor = Process(target=servidor_receber)
    servidor.start()
    servidor.join()

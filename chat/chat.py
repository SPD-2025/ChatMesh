import socket
import os
import time
from multiprocessing import Process

# Nome único baseado no hostname do container
hostname = socket.gethostname()
NOME_PEER = f"Peer-{hostname[:8]}"

# Configurações
PORTA_RECEBIMENTO = int(os.getenv('PORTA_RECEBIMENTO', 5000))
LOG_DIR = "/logs"

# Variáveis de cache para descoberta de peers
peers_cache = []
peers_last_update = 0

# Função para salvar a mensagem no log
def salvar_log(mensagem):
    os.makedirs(LOG_DIR, exist_ok=True)
    caminho_log = os.path.join(LOG_DIR, f"{NOME_PEER}_log.txt")
    with open(caminho_log, "a", encoding="utf-8") as f:
        f.write(f"{mensagem}\n")

# Função para descobrir outros peers ativos
def descobrir_peers():
    global peers_cache, peers_last_update
    agora = time.time()
    if agora - peers_last_update < 30:
        return peers_cache
    vivos = []
    for i in range(2, 20):  # range típico docker bridge
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

# Função para replicar mensagens para outros peers
def replicar_para_outros_peers(mensagem, origem_ip):
    peers = descobrir_peers()
    for ip in peers:
        if ip != origem_ip:  # Não replicar de volta para quem mandou
            try:
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.connect((ip, PORTA_RECEBIMENTO))
                client_socket.sendall(f"[REPLICATED] {mensagem}".encode())
                client_socket.close()
                print(f"[{NOME_PEER}] Replicado para {ip}")
            except Exception as e:
                print(f"[{NOME_PEER}] Erro replicando para {ip}: {e}")

# Função principal de servidor
def servidor_receber():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('', PORTA_RECEBIMENTO))
    server_socket.listen()
    print(f"[{NOME_PEER}] Servidor escutando na porta {PORTA_RECEBIMENTO}...")

    while True:
        conn, addr = server_socket.accept()
        data = conn.recv(1024)
        if data:
            mensagem = data.decode()
            print(f"[{NOME_PEER}] RECEBIDA de {addr}: {mensagem}")

            # Salvar no log
            salvar_log(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {addr} -> {mensagem}")

            # Se não for uma mensagem já replicada, replicar agora
            if not mensagem.startswith("[REPLICATED]"):
                replicar_para_outros_peers(mensagem, origem_ip=addr[0])

        conn.close()

# Iniciar servidor
if __name__ == "__main__":
    servidor = Process(target=servidor_receber)
    servidor.start()
    servidor.join()

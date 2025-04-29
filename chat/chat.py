import socket
import os
import time
from multiprocessing import Process

# Nome único baseado no hostname do container
hostname = socket.gethostname()
NOME_PEER = f"Peer-{hostname[:8]}"

# Configuração
PORTA_RECEBIMENTO = int(os.getenv('PORTA_RECEBIMENTO', 5000))
LOG_DIR = "/logs"

# Função para salvar mensagem recebida
def salvar_log(mensagem):
    os.makedirs(LOG_DIR, exist_ok=True)
    caminho_log = os.path.join(LOG_DIR, f"{NOME_PEER}_log.txt")
    with open(caminho_log, "a", encoding="utf-8") as f:
        f.write(f"{mensagem}\n")

# Função para escutar conexões
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
            salvar_log(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {addr} -> {mensagem}")
        conn.close()

if __name__ == "__main__":
    servidor = Process(target=servidor_receber)
    servidor.start()
    servidor.join()

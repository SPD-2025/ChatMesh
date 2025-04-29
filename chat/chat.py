import socket
import threading
import os
import time

# ========================
# Configurações via Ambiente
# ========================

PORTA_RECEBIMENTO = int(os.getenv('PORTA_RECEBIMENTO', 5000))
NOME_PEER = os.getenv('NOME_PEER', 'Peer')
peers_raw = os.getenv('PEERS_CONHECIDOS', '')
PEERS_CONHECIDOS = []
if peers_raw:
    for peer in peers_raw.split(','):
        ip, porta = peer.split(':')
        PEERS_CONHECIDOS.append((ip, int(porta)))
INTERVALO_ENVIO = int(os.getenv('INTERVALO_ENVIO', 5))

# Arquivo onde vamos salvar o log
LOG_FILE = f"/logs/{NOME_PEER}_log.txt"

# ========================
# Funções de Comunicação
# ========================

def registrar_log(texto):
    """Salva um texto no arquivo de log."""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    with open(LOG_FILE, 'a') as f:
        f.write(f"[{timestamp}] {texto}\n")
    print(texto)

def servidor_receber():
    """Thread para receber mensagens."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('', PORTA_RECEBIMENTO))
    server_socket.listen()

    registrar_log(f"[SERVIDOR] {NOME_PEER} aguardando conexões na porta {PORTA_RECEBIMENTO}...")

    while True:
        conn, addr = server_socket.accept()
        data = conn.recv(1024)
        if data:
            registrar_log(f"[{NOME_PEER}] MENSAGEM RECEBIDA de {addr}: {data.decode()}")
        conn.close()

def cliente_enviar():
    """Thread para enviar mensagens automáticas."""
    while True:
        mensagem = f"Hello from {NOME_PEER}!"
        for ip, porta in PEERS_CONHECIDOS:
            try:
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.connect((ip, porta))
                client_socket.sendall(mensagem.encode())
                client_socket.close()
                registrar_log(f"[{NOME_PEER}] Mensagem enviada para {ip}:{porta}")
            except Exception as e:
                registrar_log(f"[{NOME_PEER}] ERRO ao enviar para {ip}:{porta} - {e}")
        time.sleep(INTERVALO_ENVIO)

# ========================
# Execução Principal
# ========================

if __name__ == "__main__":
    # Garante que a pasta de logs exista
    os.makedirs("/logs", exist_ok=True)

    # Iniciar servidor em thread separada
    thread_servidor = threading.Thread(target=servidor_receber, daemon=True)
    thread_servidor.start()

    # Iniciar envio automático
    cliente_enviar()

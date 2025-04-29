import socket
import threading
import os
import time
import uuid
import logging
from multiprocessing import Process

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

# Buffer de mensagens pendentes
buffer_mensagens = []

# Lock para acesso concorrente ao buffer
lock_buffer = threading.Lock()

# ========================
# Funções de Comunicação
# ========================


# Configuração do logging
os.makedirs("/logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(f"/logs/{NOME_PEER}_log.txt"),
        logging.StreamHandler()
    ]
)


def servidor_receber():
    """Thread para receber mensagens e enviar ACKs."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('', PORTA_RECEBIMENTO))
    server_socket.listen()

    logging.info(f"[SERVIDOR] {NOME_PEER} aguardando conexões na porta {PORTA_RECEBIMENTO}...")

    while True:
        conn, addr = server_socket.accept()
        data = conn.recv(1024)
        if data:
            mensagem = data.decode()
            logging.info(f"[{NOME_PEER}] MENSAGEM RECEBIDA de {addr}: {mensagem}")
            
            # Se não for um ACK, responder com ACK
            if not mensagem.startswith("ACK:"):
                conn.sendall(f"ACK:{mensagem}".encode())
        conn.close()

def enviar_mensagem(ip, porta, mensagem):
    """Envia uma mensagem a um peer."""
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((ip, porta))
        client_socket.sendall(mensagem.encode())

        # Esperar resposta ACK
        ack = client_socket.recv(1024).decode()
        if ack.startswith("ACK:"):
            logging.info(f"[{NOME_PEER}] ACK recebido de {ip}:{porta} para mensagem: {mensagem}")
        client_socket.close()
    except Exception as e:
        logging.error(f"[{NOME_PEER}] ERRO ao enviar para {ip}:{porta} - {e}")
        with lock_buffer:
            buffer_mensagens.append((ip, porta, mensagem))  # Coloca no buffer para tentar de novo

def cliente_enviar():
    """Thread para enviar mensagens automáticas + reenvio de buffer."""
    while True:
        # Criar nova mensagem com ID único
        mensagem_id = str(uuid.uuid4())[:8]  # Gerar ID pequeno
        mensagem = f"{NOME_PEER}:{mensagem_id}:Hello!"

        for ip, porta in PEERS_CONHECIDOS:
            enviar_mensagem(ip, porta, mensagem)

        # Tentar reenviar mensagens do buffer
        with lock_buffer:
            if buffer_mensagens:
                logging.info(f"[{NOME_PEER}] Tentando reenviar {len(buffer_mensagens)} mensagens do buffer...")
                for ip, porta, mensagem_pendente in buffer_mensagens[:]:  # copia segura da lista
                    try:
                        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        client_socket.connect((ip, porta))
                        client_socket.sendall(mensagem_pendente.encode())
                        ack = client_socket.recv(1024).decode()
                        if ack.startswith("ACK:"):
                            logging.info(f"[{NOME_PEER}] ACK recebido (reenvio) de {ip}:{porta} para mensagem: {mensagem_pendente}")
                            buffer_mensagens.remove((ip, porta, mensagem_pendente))
                        client_socket.close()
                    except:
                        pass  # Continua no buffer

        time.sleep(INTERVALO_ENVIO)

# ========================
# Execução Principal
# ========================

if __name__ == "__main__":
    os.makedirs("/logs", exist_ok=True)
    
    # Criar socket para o servidor
    servidor = Process(target=servidor_receber)
    #cliente = Process(target=cliente_enviar)
    
    
    # Iniciar servidor em thread separada
    #thread_servidor = threading.Thread(target=servidor_receber, daemon=True)
    #thread_servidor.start()

    # Iniciar envio automático
    #cliente_enviar()
    servidor.start()
    #cliente.start()

    servidor.join()
    cliente.join()
import socket
import threading
import os
import time

# ========================
# Configurações via Ambiente
# ========================

# Porta em que o servidor vai escutar
PORTA_RECEBIMENTO = int(os.getenv('PORTA_RECEBIMENTO', 5000))

# Nome do peer (opcional, para personalizar a mensagem enviada)
NOME_PEER = os.getenv('NOME_PEER', 'Peer')

# Lista de peers conhecidos no formato: "ip1:porta1,ip2:porta2"
peers_raw = os.getenv('PEERS_CONHECIDOS', '')
PEERS_CONHECIDOS = []
if peers_raw:
    for peer in peers_raw.split(','):
        ip, porta = peer.split(':')
        PEERS_CONHECIDOS.append((ip, int(porta)))

# Intervalo de envio automático (segundos)
INTERVALO_ENVIO = int(os.getenv('INTERVALO_ENVIO', 5))

# ========================
# Funções de Comunicação
# ========================

def servidor_receber():
    """Thread para receber mensagens."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('', PORTA_RECEBIMENTO))  # Escuta em todas as interfaces
    server_socket.listen()

    print(f"[SERVIDOR] {NOME_PEER} aguardando conexões na porta {PORTA_RECEBIMENTO}...")

    while True:
        conn, addr = server_socket.accept()
        data = conn.recv(1024)
        if data:
            print(f"[{NOME_PEER}] MENSAGEM RECEBIDA de {addr}: {data.decode()}")
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
                print(f"[{NOME_PEER}] Mensagem enviada para {ip}:{porta}")
            except Exception as e:
                print(f"[{NOME_PEER}] ERRO ao enviar para {ip}:{porta} - {e}")
        time.sleep(INTERVALO_ENVIO)

# ========================
# Execução Principal
# ========================

if __name__ == "__main__":
    # Iniciar servidor em thread separada
    thread_servidor = threading.Thread(target=servidor_receber, daemon=True)
    thread_servidor.start()

    # Iniciar envio automático
    cliente_enviar()

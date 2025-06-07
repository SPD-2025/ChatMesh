import socket
import os
import time
import sqlite3
import logging
import curses
import threading
from multiprocessing import Process

HELLO_PREFIX = "__HELLO__ "


LOG_DIR = "logs"
NOME_PEER = ""
HOST_RECEBIMENTO = "0.0.0.0"
PORTA_RECEBIMENTO = 5000
PEERS = []
DB_PATH = ""

# Controle de mensagens únicas
ultimas_mensagens = []
MAX_MENSAGENS = 100

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

def carregar_novas_mensagens(ultima_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, remetente, conteudo FROM mensagens WHERE id > ? ORDER BY id",
        (ultima_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows

def replicar_para_outros_peers(mensagem, origem=None):
    """Replica a mensagem para todos os peers conhecidos.

    Se ``origem`` for informado como uma tupla ``(ip, porta)``, evita reenviar
    para esse peer.
    """

    for endereco in PEERS:
        try:
            ip, port = endereco.split(":")
            port = int(port)
        except ValueError:
            logging.error(f"Endereco invalido: {endereco}")
            continue
        if origem and ip == origem[0] and port == origem[1]:
            continue


        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((ip, port))
            client_socket.sendall(f"[REPLICATED] {mensagem}".encode())
            client_socket.close()
            logging.info(f"Replicado para {ip}:{port}")
        except Exception as e:
            logging.error(f"Erro replicando para {ip}:{port}: {e}")

def enviar_hello_para_peers():
    mensagem = f"{HELLO_PREFIX}{HOST_RECEBIMENTO}:{PORTA_RECEBIMENTO}"
    for endereco in PEERS:
        try:
            ip, port = endereco.split(":")
            port = int(port)
        except ValueError:
            logging.error(f"Endereco invalido: {endereco}")
            continue
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((ip, port))
            s.sendall(mensagem.encode())
            s.close()
        except Exception as e:
            logging.error(f"Erro enviando hello para {ip}:{port}: {e}")


def enviar_mensagem(conteudo):
    mensagem_formatada = f"{NOME_PEER}: {conteudo}"
    salvar_mensagem(NOME_PEER, conteudo)
    for endereco in PEERS:
        try:
            ip, port = endereco.split(":")
            port = int(port)
        except ValueError:
            logging.error(f"Endereco invalido: {endereco}")
            continue
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((ip, port))
            client_socket.sendall(mensagem_formatada.encode())
            client_socket.close()
            logging.info(f"Mensagem enviada para {ip}:{port}")
        except Exception as e:
            logging.error(f"Erro enviando mensagem para {ip}:{port}: {e}")


def interface_curses(stdscr):
    curses.curs_set(1)
    stdscr.clear()
    height, width = stdscr.getmaxyx()
    chat_win = curses.newwin(height - 3, width, 0, 0)
    chat_win.scrollok(True)
    input_win = curses.newwin(3, width, height - 3, 0)
    ultima_id = 0
    buffer = ""
    while True:
        for msg_id, remetente, texto in carregar_novas_mensagens(ultima_id):
            chat_win.addstr(f"{remetente}: {texto}\n")
            ultima_id = msg_id
            chat_win.refresh()

        input_win.clear()
        input_win.addstr(0, 0, "> " + buffer)
        input_win.refresh()
        input_win.timeout(500)
        ch = input_win.getch()
        if ch == -1:
            continue
        if ch in (10, 13):
            msg = buffer.strip()
            buffer = ""
            if msg.lower() == "/sair":
                break
            if msg:
                enviar_mensagem(msg)
        elif ch in (curses.KEY_BACKSPACE, 127):
            buffer = buffer[:-1]
        elif 0 <= ch < 256:
            buffer += chr(ch)


def cliente_enviar(config):
    global NOME_PEER, PEERS, DB_PATH
    NOME_PEER = config["name"]
    PEERS = config["peers"]
    DB_PATH = config["db_path"]
    curses.wrapper(interface_curses)

def servidor_receber(config):
    global HOST_RECEBIMENTO, PORTA_RECEBIMENTO, PEERS, DB_PATH, NOME_PEER
    NOME_PEER = config["name"]
    HOST_RECEBIMENTO = config["host"]
    PORTA_RECEBIMENTO = config["port"]
    PEERS = config["peers"]
    DB_PATH = config["db_path"]

    inicializar_banco()

    def _hello_loop(interval=10):
        while True:
            enviar_hello_para_peers()
            time.sleep(interval)

    threading.Thread(target=_hello_loop, daemon=True).start()

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST_RECEBIMENTO, PORTA_RECEBIMENTO))
    server_socket.listen()
    logging.info(
        f"Servidor escutando em {HOST_RECEBIMENTO}:{PORTA_RECEBIMENTO}..."
    )

    enviar_hello_para_peers()

    while True:
        conn, addr = server_socket.accept()
        data = conn.recv(1024)
        if data:
            mensagem = data.decode()
            if mensagem.startswith(HELLO_PREFIX):
                novo_peer = mensagem[len(HELLO_PREFIX):].strip()
                if novo_peer and novo_peer not in PEERS:
                    PEERS.append(novo_peer)
                    logging.info(f"Novo peer adicionado: {novo_peer}")
                    # Responde com nosso endereco para estabelecer conexao
                    try:
                        ip_resp, port_resp = novo_peer.split(":")
                        port_resp = int(port_resp)
                        resposta = f"{HELLO_PREFIX}{HOST_RECEBIMENTO}:{PORTA_RECEBIMENTO}".encode()
                        r_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        r_sock.connect((ip_resp, port_resp))
                        r_sock.sendall(resposta)
                        r_sock.close()
                    except Exception as e:
                        logging.error(f"Erro respondendo hello para {novo_peer}: {e}")
                conn.close()
                continue

            is_replicated = mensagem.startswith("[REPLICATED] ")
            mensagem_pura = mensagem[12:] if is_replicated else mensagem

            remetente, conteudo = mensagem_pura.split(":", 1)
            remetente = remetente.strip()
            conteudo = conteudo.strip()

            if not mensagem_ja_existe(remetente, conteudo):
                salvar_mensagem(remetente, conteudo)

                if not is_replicated:

                    replicar_para_outros_peers(mensagem_pura, origem=(addr[0], addr[1]))

            else:
                logging.debug("Mensagem duplicada detectada, ignorando.")

        conn.close()

if __name__ == "__main__":
    from multiprocessing import Process
    import os

    os.makedirs(LOG_DIR, exist_ok=True)

    NOME_PEER = input("Seu nome ou apelido: ").strip() or socket.gethostname()

    default_ip = socket.gethostbyname(socket.gethostname())
    ip = input(f"IP para escutar (padr\u00e3o {default_ip}): ").strip()
    HOST_RECEBIMENTO = ip or default_ip

    porta = input("Porta para escutar (padr\u00e3o 5000): ").strip()
    if porta:
        PORTA_RECEBIMENTO = int(porta)
    print(f"Escutando em {HOST_RECEBIMENTO}:{PORTA_RECEBIMENTO}")

    destinos = input(
        "Peers de destino (ip:porta separados por v\u00edrgula, opcional): "
    ).strip()
    if destinos:
        PEERS = [p.strip() for p in destinos.split(",") if p.strip()]

    DB_PATH = os.path.join(LOG_DIR, f"{NOME_PEER}.db")
    logging.basicConfig(
        filename=os.path.join(LOG_DIR, f"{NOME_PEER}.log"),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
    )

    config = {
        "name": NOME_PEER,
        "host": HOST_RECEBIMENTO,
        "port": PORTA_RECEBIMENTO,
        "peers": PEERS,
        "db_path": DB_PATH,
    }

    servidor = Process(target=servidor_receber, args=(config,))
    cliente = Process(target=cliente_enviar, args=(config,))

    servidor.start()
    cliente.start()

    servidor.join()
    cliente.join()

import sys 
import socket 
import threading 
import json 
import uuid 
import sqlite3 
import random 
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTextEdit, QListWidget, QMessageBox, QDialog,
    QListWidgetItem
)
from PySide6.QtCore import Qt, Signal, QObject, QTimer 

class MessageSignals(QObject):
    new_message = Signal(str, str, str)  
    peer_status = Signal(str, bool)  
    friend_request = Signal(str, str)  
    friend_response = Signal(str, bool) 
    update_friends_list = Signal() 
class FriendRequestDialog(QDialog):
    def __init__(self, sender_id, sender_username, parent=None):
        super().__init__(parent)
        self.sender_id = sender_id
        self.setWindowTitle("Solicitação de Amizade")
        self.setModal(True)
        layout = QVBoxLayout(self)
        message = QLabel(f"{sender_username} ({sender_id}) quer ser seu amigo!")
        accept_btn = QPushButton("Aceitar") # Botão para aceitar a solicitação.
        reject_btn = QPushButton("Rejeitar") # Botão para rejeitar a solicitação.
        accept_btn.clicked.connect(self.accept_request)
        reject_btn.clicked.connect(self.reject_request)
        layout.addWidget(message)
        layout.addWidget(accept_btn)
        layout.addWidget(reject_btn)
        
    def accept_request(self):
        self.done(1)
        
    def reject_request(self):
        self.done(0)

class P2PChat(QMainWindow):
    def __init__(self):
        super().__init__()
        self.user_id = str(uuid.uuid4())
        self.username = "" 
        self.peers = {}  
        self.active_chat = None 
        self.signals = MessageSignals() 
        self.udp_port = 50000  # Porta UDP fixa para descoberta de peers.
        self.tcp_port = self.find_free_port() # Encontra uma porta TCP livre dinamicamente.
        self.init_database() # Inicializa a conexão com o banco de dados SQLite.
        self.init_ui() # Inicializa a interface do usuário.
        self.start_network_threads() # Inicia as threads de rede para comunicação.
        self.presence_timer = QTimer(self)
        self.presence_timer.setInterval(5000) # Intervalo de 5 segundos.
        self.presence_timer.timeout.connect(self.broadcast_presence) # Conecta ao método de broadcast.
        self.presence_timer.start() # Inicia o timer.
        self.check_offline_peers_timer = QTimer(self)
        self.check_offline_peers_timer.setInterval(15000) # Intervalo de 15 segundos.
        self.check_offline_peers_timer.timeout.connect(self.check_offline_peers) # Conecta ao método de verificação.
        self.check_offline_peers_timer.start() # Inicia o timer.
        self.load_friends() # Carrega os amigos que já estão no banco de dados ao iniciar.
            
    def find_free_port(self):
        for _ in range(100):  # Tenta até 100 vezes.
            port = random.randint(49152, 65535)  # Intervalo de portas dinâmicas/privadas.
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Cria um socket TCP.
                sock.bind(('', port)) # Tenta vincular o socket a esta porta.
                sock.close() # Se o vínculo foi bem-sucedido, a porta está livre, então fecha o socket.
                return port # Retorna a porta encontrada.
            except OSError: # Captura o erro se a porta já estiver em uso.
                continue # Tenta a próxima porta.
        raise IOError("Nenhuma porta livre encontrada.") # Se não encontrar após 100 tentativas, levanta um erro.
        
    def init_database(self):
        self.conn = sqlite3.connect('chat.db') # Conecta-se ao banco de dados 'chat.db'. Se não existir, ele é criado.
        self.cursor = self.conn.cursor() # Cria um objeto cursor para executar comandos SQL.
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS profiles (
                user_id TEXT PRIMARY KEY,
                username TEXT NOT NULL
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id TEXT NOT NULL,
                receiver_id TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS friends (
                user_id TEXT NOT NULL,
                friend_id TEXT NOT NULL,
                friend_username TEXT, -- Adicionada esta coluna para armazenar o nome de usuário do amigo
                status TEXT NOT NULL, -- 'pending_sent', 'pending_received', 'accepted'
                PRIMARY KEY (user_id, friend_id)
            )
        ''')
        self.conn.commit() # Salva as alterações no banco de dados.
        print("[DATABASE] Banco de dados inicializado/verificado.") # Log de depuração.

    def init_ui(self):
        self.setWindowTitle('P2P Chat') # Define o título da janela.
        self.setGeometry(100, 100, 800, 600) # Define a posição e o tamanho da janela.
        main_widget = QWidget() # Cria um widget central para a janela.
        self.setCentralWidget(main_widget) # Define o widget central.
        layout = QHBoxLayout(main_widget) # Layout horizontal principal para dividir a janela.
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel) # Layout vertical para o painel esquerdo.
        profile_group = QWidget()
        profile_layout = QVBoxLayout(profile_group) # Layout para a seção de perfil.
        self.username_label = QLabel("Nome de Usuário: Não definido") # Rótulo para exibir o nome de usuário.
        self.user_id_label = QLabel(f"Seu ID: {self.user_id}") # Rótulo para exibir o ID do usuário.
        self.user_id_label.setWordWrap(True) # Permite que o texto do ID quebre linhas.
        copy_id_btn = QPushButton("Copiar ID") # Botão para copiar o ID do usuário.
        copy_id_btn.clicked.connect(self.copy_user_id) # Conecta o botão ao método de cópia.
        profile_layout.addWidget(self.username_label)
        profile_layout.addWidget(self.user_id_label)
        profile_layout.addWidget(copy_id_btn)
        friends_label = QLabel("Amigos") # Rótulo para a lista de amigos.
        self.friends_list = QListWidget() # Widget de lista para exibir amigos.
        self.friends_list.itemClicked.connect(self.select_chat) # Conecta o clique em um amigo para abrir o chat.
        add_friend_layout = QHBoxLayout() # Layout horizontal para o campo de adicionar amigo.
        self.friend_id_input = QLineEdit() # Campo de entrada para o ID do amigo.
        self.friend_id_input.setPlaceholderText("Digite o ID do amigo") # Texto de placeholder.
        add_friend_btn = QPushButton("Adicionar Amigo") # Botão para enviar solicitação de amizade.
        add_friend_btn.clicked.connect(self.send_friend_request) # Conecta o botão ao método de envio.
        add_friend_layout.addWidget(self.friend_id_input)
        add_friend_layout.addWidget(add_friend_btn)
        left_layout.addWidget(profile_group)
        left_layout.addWidget(friends_label)
        left_layout.addWidget(self.friends_list)
        left_layout.addLayout(add_friend_layout)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel) # Layout vertical para o painel direito.
        self.chat_display = QTextEdit() # Área de texto para exibir o histórico do chat.
        self.chat_display.setReadOnly(True) # Torna a área de chat somente leitura.
        chat_input_layout = QHBoxLayout() # Layout horizontal para o campo de entrada de mensagem.
        self.message_input = QLineEdit() # Campo de entrada para digitar mensagens.
        self.message_input.setPlaceholderText("Digite sua mensagem...") # Texto de placeholder.
        self.message_input.returnPressed.connect(self.send_message) # Conecta a tecla Enter para enviar mensagem.
        send_btn = QPushButton("Enviar") # Botão para enviar mensagem.
        send_btn.clicked.connect(self.send_message) # Conecta o botão ao método de envio.
        chat_input_layout.addWidget(self.message_input)
        chat_input_layout.addWidget(send_btn)
        right_layout.addWidget(self.chat_display)
        right_layout.addLayout(chat_input_layout)
        layout.addWidget(left_panel, 1) # Painel esquerdo ocupa 1 parte.
        layout.addWidget(right_panel, 2) # Painel direito ocupa 2 partes (maior).
        self.signals.new_message.connect(self.handle_new_message)
        self.signals.peer_status.connect(self.update_peer_status)
        self.signals.friend_request.connect(self.handle_friend_request)
        self.signals.friend_response.connect(self.handle_friend_response)
        self.signals.update_friends_list.connect(self.load_friends)
        self.show_login_dialog() # Exibe o diálogo de login ao iniciar o aplicativo.
        
    def copy_user_id(self):
        clipboard = QApplication.clipboard() # Obtém o objeto da área de transferência.
        clipboard.setText(self.user_id) # Define o texto na área de transferência.
        QMessageBox.information(self, "Sucesso", "ID de usuário copiado para a área de transferência!") # Exibe uma mensagem de sucesso.
        
    def show_login_dialog(self):
        dialog = QDialog(self) # Cria um novo diálogo.
        dialog.setWindowTitle("Login") # Define o título do diálogo.
        layout = QVBoxLayout(dialog) # Layout vertical para o diálogo.
        username_input = QLineEdit() # Campo de entrada para o nome de usuário.
        username_input.setPlaceholderText("Digite seu nome de usuário") # Texto de placeholder.
        login_btn = QPushButton("Entrar") # Botão de login.
        layout.addWidget(username_input)
        layout.addWidget(login_btn)
        
        def handle_login():
            username = username_input.text().strip() # Obtém o nome de usuário e remove espaços extras.
            if username: # Verifica se o nome de usuário não está vazio.
                self.username = username # Define o nome de usuário do aplicativo.
                self.username_label.setText(f"Nome de Usuário: {username}") # Atualiza o rótulo da UI.
                self.cursor.execute('''
                    INSERT OR REPLACE INTO profiles (user_id, username)
                    VALUES (?, ?)
                ''', (self.user_id, username))
                self.conn.commit() # Salva a alteração.
                print(f"[LOGIN] Usuário logado: {self.username} com ID {self.user_id}") # Log de depuração.
                dialog.accept() # Fecha o diálogo de login.
            else:
                QMessageBox.warning(dialog, "Erro", "Por favor, digite um nome de usuário.") # Exibe um aviso se o nome for vazio.
        login_btn.clicked.connect(handle_login) # Conecta o botão de login à função.
        dialog.exec() # Executa o diálogo (bloqueia até ser fechado).
        
    def start_network_threads(self):
        self.udp_listener_thread = threading.Thread(target=self.listen_for_peers, daemon=True)
        self.udp_listener_thread.start() # Inicia a thread.
        self.tcp_thread = threading.Thread(target=self.start_tcp_server, daemon=True)
        self.tcp_thread.start() # Inicia a thread.
        print(f"[NETWORK] Threads de rede iniciadas. UDP: {self.udp_port}, TCP: {self.tcp_port}") # Log de depuração.
            
    def broadcast_presence(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1) # Habilita a opção de broadcast.
        sock.settimeout(1) # Define um timeout para a operação de envio.
        try:
            message = json.dumps({
                'type': 'presence',
                'user_id': self.user_id,
                'username': self.username,
                'tcp_port': self.tcp_port
            })
            sock.sendto(message.encode(), ('255.255.255.255', self.udp_port))
        except Exception as e:
            print(f"Error broadcasting presence: {e}") # Log de erro.
        finally:
            sock.close() # Garante que o socket seja fechado após o envio.
            
    def listen_for_peers(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # Cria um socket UDP.
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Permite o reuso do endereço, útil para reiniciar o app.
        try:
            sock.bind(('0.0.0.0', self.udp_port)) # Vincula o socket a todas as interfaces de rede na porta UDP fixa.
            print(f"[UDP LISTENER] Escutando por peers na porta UDP {self.udp_port}") # Log de depuração.
        except Exception as e:
            print(f"Erro ao bindar socket UDP na porta {self.udp_port}: {e}") # Log de erro.
            return # Sai da thread se não conseguir bindar.
        sock.settimeout(1) # Define um timeout para a operação de recebimento para não bloquear indefinidamente.
        while True: # Loop infinito para continuar escutando.
            try:
                data, addr = sock.recvfrom(1024) # Recebe dados de um socket UDP.
                message = json.loads(data.decode()) # Decodifica a mensagem JSON.
                if message['type'] == 'presence' and message['user_id'] != self.user_id:
                    peer_id = message['user_id']
                    peer_ip = addr[0]
                    peer_port = message['tcp_port']
                    peer_username = message.get('username', 'Unknown') # Obtém o nome de usuário (com fallback).
                    self.peers[peer_id] = (peer_ip, peer_port, peer_username, datetime.now())
                    self.signals.peer_status.emit(peer_id, True)
            except socket.timeout:
                pass # Continua o loop se não receber dados no tempo limite (normal para sockets não bloqueantes).
            except json.JSONDecodeError:
                print("[UDP LISTENER] Erro ao decodificar JSON recebido.") # Log de erro para JSON inválido.
            except Exception as e:
                print(f"Error listening for peers: {e}") # Log de outros erros.
    def check_offline_peers(self):
        current_time = datetime.now() # Obtém o tempo atual.
        offline_peers = [] # Lista para armazenar IDs de peers que se tornaram offline.
        for peer_id, (ip, port, username, last_seen) in list(self.peers.items()):
            if (current_time - last_seen).total_seconds() > 10: # Se a diferença de tempo for maior que 10 segundos.
                offline_peers.append(peer_id) # Adiciona à lista de offline.
        for peer_id in offline_peers:
            if peer_id in self.peers: # Verifica se o peer ainda está no dicionário (evita erros se já foi removido).
                print(f"[PEER STATUS] Peer {self.peers[peer_id][2]} ({peer_id}) marcado como offline.") # Log de depuração.
                del self.peers[peer_id] # Remove o peer do dicionário.
                self.signals.peer_status.emit(peer_id, False) # Emite sinal para a UI para marcar como offline.
    def start_tcp_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Cria um socket TCP.
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Permite o reuso do endereço.
        server.setblocking(False) # Torna o socket não bloqueante para aceitar múltiplas conexões sem travar.
        try:
            server.bind(('0.0.0.0', self.tcp_port)) # Vincula o servidor a todas as interfaces na porta TCP.
            server.listen(5) # Começa a escutar por conexões (máximo de 5 conexões pendentes).
            print(f"[TCP SERVER] Servidor TCP iniciado na porta {self.tcp_port}") # Log de depuração.
        except Exception as e:
            print(f"Erro ao iniciar servidor TCP na porta {self.tcp_port}: {e}") # Log de erro.
            return # Sai da thread se não conseguir iniciar o servidor.
        import select # Módulo select para monitorar sockets de forma eficiente.
        inputs = [server] # Lista de sockets para monitorar (inicialmente, apenas o socket do servidor).
        while True: # Loop infinito para manter o servidor ativo.
            try:
                readable, _, _ = select.select(inputs, [], [], 1) 
                for sock in readable:
                    if sock is server: # Se o socket é o do servidor, significa que há uma nova conexão.
                        client, addr = server.accept() # Aceita a nova conexão do cliente.
                        print(f"[TCP SERVER] Conexão TCP aceita de {addr}") # Log de depuração.
                        threading.Thread(target=self.handle_tcp_connection, args=(client,), daemon=True).start()
            except Exception as e:
                print(f"Erro no loop do servidor TCP: {e}") # Log de erro.

    def handle_tcp_connection(self, client_socket):
        client_socket.setblocking(True) 
        print(f"[TCP HANDLER] Conexão tratada por thread. Socket bloqueante: {client_socket.getblocking()}") # Log de depuração.
        thread_conn = sqlite3.connect('chat.db')
        thread_cursor = thread_conn.cursor()
        try:
            data = client_socket.recv(4096).decode() # Recebe até 4096 bytes de dados e decodifica.
            if not data: # Se não houver dados, o cliente desconectou.
                print("[TCP HANDLER] Conexão TCP fechada pelo cliente (dados vazios).") # Log.
                return # Sai da função.
            message = json.loads(data) # Decodifica a string JSON para um dicionário Python.
            print(f"[TCP HANDLER] Mensagem TCP recebida: {message['type']} de {message.get('sender_id', 'N/A')}") # Log.
            if message['type'] == 'message':
                thread_cursor.execute("SELECT status FROM friends WHERE user_id = ? AND friend_id = ?", (self.user_id, message['sender_id']))
                friend_status = thread_cursor.fetchone()
                if friend_status and friend_status[0] == 'accepted': # Se for amigo aceito.
                    self.signals.new_message.emit(message['sender_id'], message['content'], message.get('timestamp', datetime.now().isoformat()))
                    print(f"[TCP HANDLER] Mensagem de chat de {message['sender_id']} para {self.user_id} processada.") # Log.
                    thread_cursor.execute('''
                        INSERT INTO messages (sender_id, receiver_id, message, timestamp)
                        VALUES (?, ?, ?, ?)
                    ''', (message['sender_id'], self.user_id, message['content'], message.get('timestamp', datetime.now().isoformat())))
                    thread_conn.commit() # Confirma a transação no banco de dados da thread.
                    print(f"[TCP HANDLER] Mensagem de chat salva no DB.") # Log.
                else:
                    print(f"[TCP HANDLER] Mensagem de {message['sender_id']} ignorada: não é amigo aceito.") # Log se não for amigo.
            elif message['type'] == 'friend_request':
                if message['receiver_id'] == self.user_id:
                    thread_cursor.execute("SELECT status FROM friends WHERE user_id = ? AND friend_id = ?", (self.user_id, message['sender_id']))
                    existing_status = thread_cursor.fetchone()
                    if not existing_status: 
                        thread_cursor.execute('''
                            INSERT INTO friends (user_id, friend_id, friend_username, status)
                            VALUES (?, ?, ?, ?)
                        ''', (self.user_id, message['sender_id'], message['sender_username'], 'pending_received'))
                        thread_conn.commit() # Confirma a transação.
                        print(f"[TCP HANDLER] Solicitação de amizade de {message['sender_id']} salva como pendente no DB da thread.") # Log.
                    self.signals.friend_request.emit(message['sender_id'], message['sender_username'])
                    print(f"[TCP HANDLER] Solicitação de amizade de {message['sender_id']} para {self.user_id} processada.") # Log.
                else:
                    print(f"[TCP HANDLER] Solicitação de amizade para {message['receiver_id']} ignorada: não é para este usuário.") # Log.
            elif message['type'] == 'friend_response':
                if message['receiver_id'] == self.user_id:
                    if message['accepted']:
                        thread_cursor.execute('''
                            UPDATE friends
                            SET status = 'accepted'
                            WHERE user_id = ? AND friend_id = ?
                        ''', (self.user_id, message['sender_id']))
                        thread_conn.commit() # Confirma a transação.
                        print(f"[TCP HANDLER] Resposta de amizade 'Aceito' de {message['sender_id']} atualizada no DB da thread.") # Log.
                    else:
                        thread_cursor.execute('''
                            DELETE FROM friends
                            WHERE user_id = ? AND friend_id = ? AND status = 'pending_sent'
                        ''', (self.user_id, message['sender_id']))
                        thread_conn.commit() # Confirma a transação.
                        print(f"[TCP HANDLER] Resposta de amizade 'Rejeitado' de {message['sender_id']} removida do DB da thread.") # Log.
                    self.signals.friend_response.emit(message['sender_id'], message['accepted'])
                    print(f"[TCP HANDLER] Resposta de amizade de {message['sender_id']} para {self.user_id} processada (Aceita: {message['accepted']}).") # Log.
                else:
                    print(f"[TCP HANDLER] Resposta de amizade para {message['receiver_id']} ignorada: não é para este usuário.") # Log.
        except json.JSONDecodeError:
            print("[TCP HANDLER] Mensagem JSON malformada recebida.") # Log de erro JSON.
        except Exception as e:
            print(f"[TCP HANDLER ERROR] Erro inesperado ao lidar com conexão TCP: {e}") # Log de erro geral.
        finally:
            client_socket.close() # Garante que o socket do cliente seja fechado.
            thread_conn.close() # ESSENCIAL: Fecha a conexão do banco de dados criada para esta thread.
            print("[TCP HANDLER] Conexão DB da thread fechada.") # Log.
    def send_friend_request(self):
        friend_id = self.friend_id_input.text().strip() # Obtém o ID do campo de entrada.
        if not friend_id: # Validação do ID.
            QMessageBox.warning(self, "Erro", "Por favor, digite o ID do amigo.")
            return
        if friend_id == self.user_id: # Não pode adicionar a si mesmo.
            QMessageBox.warning(self, "Erro", "Você não pode se adicionar como amigo.")
            return
        self.cursor.execute("SELECT status FROM friends WHERE user_id = ? AND friend_id = ?", (self.user_id, friend_id))
        existing_friend = self.cursor.fetchone()
        if existing_friend: # Se já existe um status de amizade.
            if existing_friend[0] == 'accepted':
                QMessageBox.information(self, "Info", "Este usuário já é seu amigo.")
            elif existing_friend[0] == 'pending_sent':
                QMessageBox.information(self, "Info", "Solicitação de amizade já enviada para este usuário.")
            elif existing_friend[0] == 'pending_received':
                QMessageBox.information(self, "Info", "Você tem uma solicitação de amizade pendente deste usuário. Por favor, aceite-a.")
            return
        if friend_id in self.peers: # Verifica se o amigo está atualmente descoberto na rede.
            ip, port, username, _ = self.peers[friend_id] # Obtém IP, porta e nome de usuário do peer.
            print(f"[FRIEND REQUEST] Tentando enviar solicitação para {username} ({friend_id}) em {ip}:{port}") # Log.
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Cria um socket TCP.
                sock.settimeout(5) # Define um timeout para a conexão.
                sock.connect((ip, port)) # Tenta conectar ao peer.
                print(f"[FRIEND REQUEST] Conectado com sucesso a {ip}:{port}") # Log.
                data = json.dumps({
                    'type': 'friend_request',
                    'sender_id': self.user_id,
                    'sender_username': self.username,
                    'receiver_id': friend_id
                })
                sock.send(data.encode()) # Envia a mensagem.
                sock.close() # Fecha o socket.
                print(f"[FRIEND REQUEST] Dados da solicitação de amizade enviados para {friend_id}") # Log.
                self.cursor.execute('''
                    INSERT INTO friends (user_id, friend_id, friend_username, status)
                    VALUES (?, ?, ?, ?)
                ''', (self.user_id, friend_id, username, 'pending_sent'))
                self.conn.commit() # Salva a alteração.
                QMessageBox.information(self, "Sucesso", "Solicitação de amizade enviada!") # Mensagem de sucesso.
                self.friend_id_input.clear() # Limpa o campo de entrada.
            except socket.timeout: # Erro se o tempo limite de conexão for excedido.
                QMessageBox.warning(self, "Erro", f"Tempo limite excedido ao tentar conectar ao peer {username} ({friend_id}). Ele pode estar offline ou o firewall bloqueando.")
                print(f"[FRIEND REQUEST ERROR] Tempo limite de conexão para {friend_id}.") # Log de erro.
            except ConnectionRefusedError: # Erro se a conexão for recusada pelo peer.
                QMessageBox.warning(self, "Erro", f"Conexão recusada pelo peer {username} ({friend_id}). Verifique o firewall ou se ele está rodando.")
                print(f"[FRIEND REQUEST ERROR] Conexão recusada para {friend_id}.") # Log de erro.
            except Exception as e: # Outros erros.
                QMessageBox.warning(self, "Erro", f"Falha ao enviar solicitação de amizade: {e}")
                print(f"[FRIEND REQUEST ERROR] Falha geral ao enviar para {friend_id}: {e}") # Log de erro.
        else:
            QMessageBox.warning(self, "Erro", "Usuário não encontrado na rede ou offline. Por favor, certifique-se de que ele esteja online.")
            print(f"[FRIEND REQUEST ERROR] ID {friend_id} não encontrado em self.peers. Peers atuais: {self.peers.keys()}") # Log de erro.
    def handle_friend_request(self, sender_id, sender_username):
        self.cursor.execute("SELECT status FROM friends WHERE user_id = ? AND friend_id = ?", (self.user_id, sender_id))
        existing_status = self.cursor.fetchone()
        if existing_status and existing_status[0] == 'accepted':
            print(f"Já amigo de {sender_username} ({sender_id}). Ignorando solicitação.") # Log.
            return
        if not existing_status or existing_status[0] != 'pending_received': 
            self.cursor.execute('''
                INSERT OR REPLACE INTO friends (user_id, friend_id, friend_username, status)
                VALUES (?, ?, ?, ?)
            ''', (self.user_id, sender_id, sender_username, 'pending_received'))
            self.conn.commit() # Salva a alteração.
            print(f"[FRIEND REQUEST HANDLER] Solicitação de amizade de {sender_username} ({sender_id}) salva como pendente.") # Log.
        dialog = FriendRequestDialog(sender_id, sender_username, self)
        result = dialog.exec() # Executa o diálogo e obtém o resultado (1 para aceitar, 0 para rejeitar).
        if result == 1:  # Se a solicitação foi aceita.
            print(f"[FRIEND REQUEST HANDLER] Solicitação de {sender_username} ({sender_id}) ACEITA.") # Log.
            self.cursor.execute('''
                UPDATE friends
                SET status = 'accepted', friend_username = ?
                WHERE user_id = ? AND friend_id = ?
            ''', (sender_username, self.user_id, sender_id))
            self.conn.commit() # Salva a alteração.
            self.add_friend_to_list(sender_id, sender_username, online=True) # Assume online já que enviou a solicitação.
            self.send_friend_response(sender_id, accepted=True)
            QMessageBox.information(self, "Solicitação de Amizade", f"Você agora é amigo de {sender_username}!") # Mensagem para o usuário.
        else:  # Se a solicitação foi rejeitada.
            print(f"[FRIEND REQUEST HANDLER] Solicitação de {sender_username} ({sender_id}) REJEITADA.") # Log.
            self.cursor.execute('''
                DELETE FROM friends
                WHERE user_id = ? AND friend_id = ? AND status = 'pending_received'
            ''', (self.user_id, sender_id))
            self.conn.commit() # Salva a alteração.
            self.send_friend_response(sender_id, accepted=False) # Envia resposta de rejeição ao outro peer.
            QMessageBox.information(self, "Solicitação de Amizade", f"Você rejeitou a solicitação de amizade de {sender_username}.") # Mensagem para o usuário.
    def send_friend_response(self, receiver_id, accepted):
        if receiver_id in self.peers: # Verifica se o peer está online para enviar a resposta.
            ip, port, _, _ = self.peers[receiver_id] # Obtém informações do peer.
            print(f"[FRIEND RESPONSE] Enviando resposta '{'Aceito' if accepted else 'Rejeitado'}' para {receiver_id} em {ip}:{port}") # Log.
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Cria um socket TCP.
                sock.settimeout(5) # Timeout para a conexão.
                sock.connect((ip, port)) # Conecta ao peer.
                data = json.dumps({
                    'type': 'friend_response',
                    'sender_id': self.user_id,
                    'receiver_id': receiver_id,
                    'accepted': accepted,
                    'sender_username': self.username # Inclui o nome de usuário do remetente.
                })
                sock.send(data.encode()) # Envia a mensagem.
                sock.close() # Fecha o socket.
                print(f"[FRIEND RESPONSE] Resposta de amizade enviada com sucesso para {receiver_id}.") # Log.
            except socket.timeout:
                print(f"[FRIEND RESPONSE ERROR] Tempo limite ao enviar resposta para {receiver_id}.") # Log de erro.
            except ConnectionRefusedError:
                print(f"[FRIEND RESPONSE ERROR] Conexão recusada ao enviar resposta para {receiver_id}.") # Log de erro.
            except Exception as e:
                print(f"Erro ao enviar resposta de amigo para {receiver_id}: {e}") # Log de erro.
        else:
            print(f"Peer {receiver_id} não encontrado para enviar resposta de amigo.") # Log se o peer estiver offline.
    def handle_friend_response(self, sender_id, accepted):
        if accepted: # Se a resposta foi 'aceito'.
            print(f"[FRIEND RESPONSE HANDLER] Recebido resposta 'Aceito' de {sender_id}.") # Log.
            self.cursor.execute('''
                UPDATE friends
                SET status = 'accepted'
                WHERE user_id = ? AND friend_id = ?
            ''', (self.user_id, sender_id))
            self.conn.commit() # Salva a alteração.
            sender_username = self.peers.get(sender_id, ["", "", sender_id])[2] 
            self.add_friend_to_list(sender_id, sender_username, online=True) # Adiciona/atualiza o amigo na UI.
            QMessageBox.information(self, "Solicitação de Amizade", f"Sua solicitação de amizade para {sender_username} foi aceita!") # Mensagem ao usuário.
        else: # Se a resposta foi 'rejeitado'.
            print(f"[FRIEND RESPONSE HANDLER] Recebido resposta 'Rejeitado' de {sender_id}.") # Log.
            self.cursor.execute('''
                DELETE FROM friends
                WHERE user_id = ? AND friend_id = ? AND status = 'pending_sent'
            ''', (self.user_id, sender_id))
            self.conn.commit() # Salva a alteração.
            sender_username = self.peers.get(sender_id, ["", "", sender_id])[2]
            QMessageBox.information(self, "Solicitação de Amizade", f"Sua solicitação de amizade para {sender_username} foi rejeitada.") # Mensagem ao usuário.
        self.signals.update_friends_list.emit() # Emite sinal para garantir que a lista de amigos na UI esteja atualizada.
    def load_friends(self):
        self.friends_list.clear() # Limpa a lista atual na UI.
        self.cursor.execute("SELECT friend_id, friend_username, status FROM friends WHERE user_id = ? AND status = 'accepted'", (self.user_id,))
        for friend_id, friend_username, status in self.cursor.fetchall():
            online = friend_id in self.peers
            self.add_friend_to_list(friend_id, friend_username, online) # Adiciona o amigo à lista da UI.
        print(f"[FRIENDS] Amigos carregados para {self.username}. Total: {self.friends_list.count()}") # Log.
    def add_friend_to_list(self, friend_id, friend_username, online=False):
        updated = False
        for i in range(self.friends_list.count()):
            item = self.friends_list.item(i)
            if item.data(Qt.UserRole) == friend_id: # Usa Qt.UserRole para armazenar o ID real do amigo no item.
                status_icon = "🟢" if online else "⚫" # Define o ícone de status.
                current_text = item.text()
                username_display = friend_username # Prioriza o nome de usuário passado como argumento.
                if '(' in current_text and ')' in current_text:
                    username_display = current_text[current_text.find(' ')+1 : current_text.rfind('(')].strip()
                elif current_text.startswith("🟢 ") or current_text.startswith("⚫ "):
                    username_display = current_text[2:].strip() # Remove apenas o ícone inicial.
                else:
                    username_display = current_text.strip() # Se não tem ícone, usa o texto todo.
                item.setText(f"{status_icon} {username_display} ({friend_id})")
                print(f"[UI STATUS] Status de amigo {username_display} ({friend_id}) atualizado para {'online' if online else 'offline'}.") # Log.
                updated = True
                return # Sai da função pois o amigo foi atualizado.
        status_icon = "🟢" if online else "⚫"
        display_text = f"{status_icon} {friend_username} ({friend_id})" # Texto a ser exibido.
        item = QListWidgetItem(display_text) # Cria um novo item de lista.
        item.setData(Qt.UserRole, friend_id) # Armazena o ID real do amigo no item para fácil recuperação.
        self.friends_list.addItem(item) # Adiciona o item à QListWidget.
        print(f"[UI] Amigo {friend_username} ({friend_id}) adicionado à lista.") # Log.
    def send_message(self):
        if not self.active_chat: # Verifica se há um chat ativo selecionado.
            QMessageBox.warning(self, "Erro", "Por favor, selecione um amigo para conversar.")
            return
        message = self.message_input.text().strip() # Obtém o texto da mensagem.
        if not message: # Não envia mensagem vazia.
            return
        peer_id = self.active_chat # ID do amigo para quem enviar a mensagem.
        if peer_id in self.peers: # Verifica se o amigo está online e descoberto.
            ip, port, username, _ = self.peers[peer_id] # Obtém informações do amigo.
            print(f"[MESSAGE SEND] Tentando enviar mensagem para {username} ({peer_id}) em {ip}:{port}") # Log.
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Cria um socket TCP.
                sock.settimeout(5) # Timeout para a conexão.
                sock.connect((ip, port)) # Conecta ao amigo.
                current_timestamp = datetime.now().isoformat() # Obtém o timestamp atual.
                data = json.dumps({
                    'type': 'message',
                    'sender_id': self.user_id,
                    'content': message,
                    'timestamp': current_timestamp
                })
                sock.send(data.encode()) # Envia a mensagem.
                sock.close() # Fecha o socket.
                print(f"[MESSAGE SEND] Mensagem enviada para {peer_id}.") # Log.
                self.chat_display.append(f"Você ({datetime.now().strftime('%H:%M')}): {message}")
                self.cursor.execute('''
                    INSERT INTO messages (sender_id, receiver_id, message, timestamp)
                    VALUES (?, ?, ?, ?)
                ''', (self.user_id, peer_id, message, current_timestamp))
                self.conn.commit() # Salva a alteração.
                self.message_input.clear() # Limpa o campo de entrada de mensagem.
            except socket.timeout:
                QMessageBox.warning(self, "Erro", f"Tempo limite excedido ao tentar enviar mensagem para {username} ({peer_id}).")
                print(f"[MESSAGE SEND ERROR] Tempo limite de conexão para {peer_id}.") # Log de erro.
            except ConnectionRefusedError:
                QMessageBox.warning(self, "Erro", f"Conexão recusada pelo amigo {username} ({peer_id}). Ele pode estar offline ou o firewall bloqueando.")
                print(f"[MESSAGE SEND ERROR] Conexão recusada para {peer_id}.") # Log de erro.
            except Exception as e:
                QMessageBox.warning(self, "Erro", f"Falha ao enviar mensagem: {e}")
                print(f"[MESSAGE SEND ERROR] Falha geral ao enviar para {peer_id}: {e}") # Log de erro.
        else:
            QMessageBox.warning(self, "Erro", f"Amigo {self.peers.get(peer_id, ['','',peer_id])[2]} está offline. Não foi possível enviar mensagem.")
            print(f"[MESSAGE SEND ERROR] Amigo {peer_id} não está nos peers online.") # Log de erro.
    def handle_new_message(self, sender_id, message, timestamp_str):
        self.cursor.execute("SELECT friend_username FROM friends WHERE user_id = ? AND friend_id = ?", (self.user_id, sender_id))
        result = self.cursor.fetchone()
        sender_username = result[0] if result else "Desconhecido"
        print(f"[NEW MESSAGE] Mensagem recebida de {sender_username} ({sender_id}).") # Log.
        if self.active_chat == sender_id:
            display_time = datetime.fromisoformat(timestamp_str).strftime('%H:%M') # Formata o timestamp.
            self.chat_display.append(f"{sender_username} ({display_time}): {message}") # Adiciona a mensagem ao display.
    def select_chat(self, item):
        self.active_chat = item.data(Qt.UserRole) # Obtém o ID real do amigo selecionado.
        print(f"[CHAT SELECT] Chat ativo alterado para {self.active_chat}") # Log.
        friend_username = "Amigo Desconhecido"
        if self.active_chat in self.peers: # Tenta obter o nome do peer se estiver online.
            friend_username = self.peers[self.active_chat][2]
        else: # Se offline, tenta obter o nome do banco de dados de amigos.
            self.cursor.execute("SELECT friend_username FROM friends WHERE user_id = ? AND friend_id = ?", (self.user_id, self.active_chat))
            result = self.cursor.fetchone()
            if result:
                friend_username = result[0]
        self.chat_display.setHtml(f"<h3>Conversa com {friend_username} ({self.active_chat})</h3><hr>") # Define o cabeçalho.
        self.chat_display.clear() # Limpa o display de chat atual.
        self.cursor.execute('''
            SELECT sender_id, message, timestamp
            FROM messages
            WHERE (sender_id = ? AND receiver_id = ?)
                OR (sender_id = ? AND receiver_id = ?)
            ORDER BY timestamp
        ''', (self.user_id, self.active_chat, self.active_chat, self.user_id))
        for sender_id, message, timestamp_str in self.cursor.fetchall():
            prefix = "Você" # Se a mensagem foi enviada por este usuário.
            if sender_id != self.user_id: # Se a mensagem foi recebida de outro.
                self.cursor.execute("SELECT friend_username FROM friends WHERE user_id = ? AND friend_id = ?", (self.user_id, sender_id))
                result = self.cursor.fetchone()
                prefix = result[0] if result else "Amigo"
            display_time = datetime.fromisoformat(timestamp_str).strftime('%H:%M') # Formata o timestamp.
            self.chat_display.append(f"{prefix} ({display_time}): {message}") # Adiciona a mensagem ao display.
    def update_peer_status(self, peer_id, online):
        updated = False
        for i in range(self.friends_list.count()):
            item = self.friends_list.item(i)
            if item.data(Qt.UserRole) == peer_id: # Compara o ID armazenado no item.
                status_icon = "🟢" if online else "⚫" # Define o ícone de status.
                current_text = item.text()
                username_display = "Desconhecido"
                if '(' in current_text and ')' in current_text:
                    username_display = current_text[current_text.find(' ')+1 : current_text.rfind('(')].strip()
                elif current_text.startswith("🟢 ") or current_text.startswith("⚫ "):
                    username_display = current_text[2:].strip()
                else:
                    username_display = current_text.strip()
                item.setText(f"{status_icon} {username_display} ({peer_id})")
                print(f"[UI STATUS] Status de amigo {username_display} ({peer_id}) atualizado para {'online' if online else 'offline'}.") # Log.
                updated = True
                return # Sai da função pois o item foi atualizado.
        if online and not updated:
            self.cursor.execute("SELECT friend_username FROM friends WHERE user_id = ? AND friend_id = ? AND status = 'accepted'", (self.user_id, peer_id))
            result = self.cursor.fetchone()
            if result:
                friend_username = result[0]
                self.add_friend_to_list(peer_id, friend_username, online=True) # Adiciona o amigo à lista da UI.
                print(f"[UI STATUS] Amigo {friend_username} ({peer_id}) adicionado à lista após ficar online.") # Log.
            else:
                print(f"[UI STATUS] Peer {peer_id} online, mas não é um amigo aceito.") # Log.
    def closeEvent(self, event):
        print("[APP] Fechando aplicação. Fechando conexão com o banco de dados.") # Log.
        self.conn.close() # Fecha a conexão principal do banco de dados.
        event.accept() # Aceita o evento de fechamento, permitindo que a janela seja fechada.
if __name__ == '__main__':
    app = QApplication(sys.argv) # Cria uma instância do aplicativo Qt.
    window = P2PChat() # Cria uma instância da sua janela principal de chat.
    window.show() # Exibe a janela.
    sys.exit(app.exec()) # Inicia o loop de eventos do Qt e sai do programa quando a janela é fechada.

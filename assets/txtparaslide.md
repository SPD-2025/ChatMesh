**Apresentação Projeto ChatMesh - Sistema de Comunicação Distribuída P2P**

---

**Slide 1 - Título**

> ChatMesh: Sistema de Comunicação Distribuída P2P com Tolerância a Falhas
>
> Projeto de Desenvolvimento de Soluções com Sistemas Paralelos e Distribuídos

---

**Slide 2 - Introdução**

- Desenvolvimento de um sistema P2P para troca de mensagens.
- Cada peer atua como cliente e servidor.
- Utilização de Docker para isolação e distribuição.

---

**Slide 3 - Objetivos**

- Eliminar ponto único de falha.
- Garantir entrega confiável de mensagens.
- Demonstrar paralelismo real com multiprocessing.
- Persistência de logs via volumes Docker.

---

**Slide 4 - Arquitetura**

- 2 ou mais peers Dockerizados
- Comunicação via TCP/IP
- Volume Docker compartilhado `/logs`
- Processos independentes para envio e recebimento

**Diagrama:**

Peer1 ↔ Peer2
(Volume /logs compartilhado)

---

**Slide 5 - Funcionalidades Implementadas**

- Envio automático de mensagens com IDs únicos.
- Buffer de reenvio para mensagens não confirmadas.
- Confirmação ACK de recebimento.
- Multiprocessing para paralelismo real.
- Logging profissional com rotinas de persistência.

---

**Slide 6 - Tecnologias Utilizadas**

- Python 3.11
- Docker + Docker Compose
- Sockets TCP
- Multiprocessing
- Logging oficial do Python

---

**Slide 7 - Robustez e Tolerância a Falhas**

- Bufferização e reenviio automático de mensagens.
- Persistência de logs mesmo após falhas.
- Isolamento total de processo entre servidor e cliente.
- Entrega confiável usando confirmações ACK.

---

**Slide 8 - Resultados Observados**

- Comunicação mantida mesmo com falhas temporárias.
- Mensagens corretamente rastreadas e auditadas.
- Logs centralizados facilitam auditoria e depuração.

---

**Slide 9 - Melhorias Futuras**

- Suporte à adição dinâmica de novos peers.
- Implementação de criptografia nas comunicações.
- Integração com sistemas de monitoramento.

---

**Slide 10 - Encerramento**

> ChatMesh demonstra na prática conceitos avançados de sistemas distribuídos, tolerância a falhas e comunicação paralela confiável.
>
> Obrigado!

---

(Notas para o apresentador: enfatizar a robustez, a eliminação de single point of failure e a escalabilidade do sistema.)


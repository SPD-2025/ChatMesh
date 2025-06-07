# ChatMesh

_Um chat distribuído P2P_

- Por que ChatMesh? Em inglês, "mesh" significa "malha". No contexto de redes de computadores e Wi-Fi, "mesh" se refere a um sistema de rede onde múltiplos dispositivos (como roteadores) se conectam entre si para criar uma rede de cobertura ampla e consistente.

## INTEGRANTES

[João Antonio dos Santos Ilario](https://github.com/JoaoPalmasBR)

[Emmanuel de Oliveira Peralta](https://github.com/Emmanuelperalta8)

[Felipe Nóbrega Cardoso Pardo](https://github.com/FelipeNoobrega)

[Nathan Aguiar Silva](https://github.com/nathansilvaa)

## Objetivo do Projeto

## Desenvolver um sistema de comunicação de mensagens chamado ChatMesh, onde os participantes se conectam diretamente entre si (modelo Peer-to-Peer), formando uma rede de troca de mensagens distribuída, sem servidor central.

## Como executar

Instale as dependências:

```bash
pip install -r requirements.txt
```

Execute o script e siga as instruções interativas para definir seu nome, a porta de escuta e os peers de destino:

```bash
python chat.py
```

Abra um terminal para cada instância desejada e informe dados diferentes quando solicitado.

## Trabalho:

Projeto de Desenvolvimento de Soluções com Sistemas Paralelos e Distribuídos
Desenvolver uma solução computacional que explore os conceitos de paralelismo e distribuição para resolver um problema real, utilizando ferramentas e frameworks que simplifiquem a implementação.

### Etapas da Atividade:

- Definição do Problema `28-04-2025`

  - Escolher um problema que se beneficie de paralelismo ou distribuição.
    - Fazer um chat distribuido usando as tecnicas P2P
  - Justificar por que a abordagem paralela/distribuída é vantajosa.
    - Evitar que a esturura dependa de um único servidor caindo e derrubando o sistema.
    - Melhor escalabilidade (mais usuários = mais nós).
    - Melhor tolerância a falhas.
    - Menor latência entre peers próximos.

- Projeto da Solução

  - Definir a arquitetura (ex.: mestre-trabalhador, MapReduce, microsserviços). `29-04-2025`
    - Arquitetura:
      - P2P (Cada nó se conecta a outros)
    - Paralelismo para:
      - Recepção de mensagens em threads separadas.
      - Envio e recepção simultâneos
    - Protocolo:
      - TCP com sockets (para garantir a integridade)
  - Escolher as ferramentas e justificar a seleção.
    - PYTHON: Ja utilizamos em aula e temos o conceito de paralelismo e
      alta disponibilidade
    - Bibliotecas:
      - ``
      - `socket`
      - `multiprocessing`
      - `datetime`
      - `logging`
      - `os`

- Implementação

  - Desenvolver o código utilizando um framework de paralelismo/distribuição.
  - Garantir que a solução seja escalável e tolerante a falhas (se aplicável).

- Testes e Análise

  - Comparar o desempenho com uma versão sequencial (se possível).
  - Medir speedup, eficiência ou throughput.

- Apresentação
  - Demonstrar o funcionamento da solução.
  - Discutir desafios e possíveis melhorias.

### Link para dicas de Markdown

[Markdown Guide](https://www.markdownguide.org/cheat-sheet/)
a

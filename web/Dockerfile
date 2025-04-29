# Usar imagem base oficial do Python
FROM python:3.11-slim

# Diretório de trabalho dentro do container
WORKDIR /web

# Copiar e instalar as dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o restante do código
COPY . .

# Comando para rodar (o docker-compose já sobrescreve, mas deixar aqui por segurança)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

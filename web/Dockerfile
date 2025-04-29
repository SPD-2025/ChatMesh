# Usar imagem base oficial do Python
FROM python:3.11-slim

# Diretório de trabalho dentro do container
WORKDIR /app

# Copiar e instalar as dependências
COPY . .

RUN pip install --no-cache-dir -r requirements.txt

# Copiar o restante do código
COPY . .

# Executar Uvicorn diretamente, sem --reload em produção
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

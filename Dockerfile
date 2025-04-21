# Use a imagem oficial do Python como base
FROM python:3.12-slim

# Define o diretório de trabalho no container
WORKDIR /app

# Copia os arquivos de requisitos para o container
COPY requirements.txt .

# Instala as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copia o resto do código da aplicação
COPY src/ ./src/
COPY logs/ ./logs/
COPY msep.md .

# Comando para rodar a aplicação
CMD ["python", "src/api.py"]
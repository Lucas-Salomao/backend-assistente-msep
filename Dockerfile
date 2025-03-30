# Use a imagem oficial do Python como base
FROM python:3.12-slim

# Define o diretório de trabalho no container
WORKDIR /app

# Copia os arquivos de requisitos para o container
COPY requirements.txt .

# Instala as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copia o resto do código da aplicação
COPY . .

# Define a variável de ambiente para a porta
ENV PORT=8000

# Expõe a porta 8000
EXPOSE 8000

# Comando para rodar a aplicação
CMD ["python", "src/api.py"]
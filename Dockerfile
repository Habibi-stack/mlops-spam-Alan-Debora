# Usa a imagem oficial Python recomendada pelo guia do CETAM
FROM python:3.11-slim

# Evita geracao de arquivos .pyc e forca saida em tempo real de logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Diretorio de trabalho no conteiner
WORKDIR /app

# Copia e instala as dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copia os modulos da aplicacao e o modelo serializado
COPY app/ ./app/
COPY model/ ./model/

# Porta de comunicacao da aplicacao FastAPI
EXPOSE 8000

# Variaveis de ambiente padrao (podem ser substituidas em execucao)
ENV APP_ENV=dev
ENV MODEL_VERSION=v1
ENV API_KEY=chave-ficticia-123

# Inicializacao da API via Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

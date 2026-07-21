FROM python:3.11-slim

WORKDIR /app

# Instala dependências do sistema + Node.js (necessário para yt-dlp descriptografar URLs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    ca-certificates \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Baixa o yt-dlp no build (internet disponível em build time)
RUN curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp \
    && chmod +x /usr/local/bin/yt-dlp

COPY . .

# Porta padrão (Railway/Koyeb usam $PORT)
ENV PORT=5000
EXPOSE $PORT

CMD gunicorn app:app --bind 0.0.0.0:$PORT

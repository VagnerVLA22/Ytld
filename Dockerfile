FROM python:3.11-slim

WORKDIR /app

# Instala dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instala yt-dlp via pip (já inclui EJS para descriptografar URLs, não precisa de Node.js separado)
RUN pip install --no-cache-dir yt-dlp

COPY . .

# Porta padrão (Railway/Koyeb usam $PORT)
ENV PORT=5000
EXPOSE $PORT

CMD gunicorn app:app --bind 0.0.0.0:$PORT

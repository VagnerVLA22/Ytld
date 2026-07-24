FROM python:3.11-slim

WORKDIR /app

# Instala dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    ffmpeg \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Instala Deno (runtime JS necessário para yt-dlp resolver challenges do YouTube)
RUN curl -fsSL https://github.com/denoland/deno/releases/latest/download/deno-x86_64-unknown-linux-gnu.zip -o /tmp/deno.zip \
    && unzip /tmp/deno.zip -d /usr/local/bin \
    && rm /tmp/deno.zip \
    && chmod +x /usr/local/bin/deno \
    && deno --version

COPY requirements.txt .
RUN pip install --no-cache-dir -U "yt-dlp[default]"

COPY . .

ENV PORT=5000
EXPOSE $PORT

CMD gunicorn app:app --bind 0.0.0.0:$PORT

FROM python:3.11-slim

WORKDIR /app

# Instala dependências do sistema + Deno (runtime JS recomendado pelo yt-dlp para resolver challenges)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    ffmpeg \
    unzip \
    && curl -fsSL https://deno.land/install.sh | sh \
    && rm -rf /var/lib/apt/lists/*

# Deno no PATH
ENV DENO_INSTALL="/root/.deno"
ENV PATH="$DENO_INSTALL/bin:$PATH"

# Verifica Deno
RUN deno --version

COPY requirements.txt .
RUN pip install --no-cache-dir -U "yt-dlp[default]"

COPY . .

ENV PORT=5000
EXPOSE $PORT

CMD gunicorn app:app --bind 0.0.0.0:$PORT

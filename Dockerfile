FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    ca-certificates \
    xz-utils \
    && rm -rf /var/lib/apt/lists/*

# Node.js 22 LTS (necessário para yt-dlp EJS, mínimo v22)
RUN curl -fsSL https://nodejs.org/dist/v22.16.0/node-v22.16.0-linux-x64.tar.xz | tar -xJ -C /usr/local --strip-components=1 \
    && node --version

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN pip install --no-cache-dir yt-dlp yt-dlp-ejs

COPY . .

ENV PORT=5000
EXPOSE $PORT

CMD gunicorn app:app --bind 0.0.0.0:$PORT

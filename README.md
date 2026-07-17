# YouTube Downloader (Web App)

Aplicação Flask que usa yt-dlp + ffmpeg para baixar vídeos e áudios do YouTube.
Funciona localmente (Windows) e em deploy na nuvem (Linux).

## Executar localmente (Windows)

1. Tenha `yt-dlp.exe` e `ffmpeg.exe` na pasta raiz (já inclusos)
2. Instale dependências: `pip install -r requirements.txt`
3. Rode: `python app.py`
4. Acesse http://localhost:5000

## Deploy GRATUITO na nuvem

O app baixa yt-dlp automaticamente no startup (Linux). O ffmpeg pode vir
via Dockerfile (apt) ou ser baixado automaticamente se não existir.

### 1. Railway (Free — $5 crédito/mês, ~500h, sem cartão p/ começar)
- Conecte o repositório GitHub
- O `Procfile` é usado: `web: gunicorn app:app --bind 0.0.0.0:$PORT`
- Ou use o `Dockerfile` (recomendado, já traz ffmpeg)

### 2. Render (Free — sem cartão para free tier de web service)
- "New Web Service" → conecte o repo
- O `render.yaml` é detectado (plano free, Python 3.11)
- Build: `pip install -r requirements.txt` | Start: gunicorn

### 3. Koyeb (Free — generoso, sem cartão)
- Conecte GitHub e use o `Dockerfile` (Koyeb builda a imagem)
- Defina a porta como `PORT` (já tratada no app)

### 4. Fly.io (Free limitado — 3 VMs pequenas por 3 meses)
- `fly launch` (usa Procfile/Dockerfile) → `fly deploy`

### Não recomendados (bloqueiam yt-dlp):
- PythonAnywhere (rede bloqueia download do YouTube)
- Netlify (não roda executáveis/binários)

## Docker (local ou qualquer PaaS)

```
docker build -t yt-downloader .
docker run -p 5000:5000 -e PORT=5000 yt-downloader
```

## Variáveis de ambiente
- `PORT` — porta do servidor (usada automaticamente em PaaS)

## Estrutura
- `app.py` — backend Flask
- `templates/index.html` — interface web responsiva
- `requirements.txt` — dependências
- `Procfile` / `render.yaml` / `Dockerfile` — config de deploy

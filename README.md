# YouTube Downloader (Web App) — "Ytld"

Aplicação Flask que usa yt-dlp + ffmpeg para baixar vídeos e áudios do YouTube.
Repositório: https://github.com/VagnerVLA22/Ytld

## Executar localmente (Windows)

1. Tenha `yt-dlp.exe` e `ffmpeg.exe` na pasta raiz
2. `pip install -r requirements.txt`
3. `python app.py`
4. Acesse http://localhost:5000

## Deploy GRATUITO (recomendado)

O app baixa yt-dlp no startup (Linux). O ffmpeg vem via Dockerfile (apt)
ou é baixado automaticamente se não existir.

### Railway (Free — ~500h/mês, sem cartão p/ começar) ⭐
1. Acesse https://railway.app e "Login with GitHub"
2. "New Project" → "Deploy from GitHub repo" → selecione **Ytld**
3. Railway detecta o `Procfile` automaticamente
4. O app sobe em `https://<seu-app>.railway.app`

### Render (Free — sem cartão para free tier) ⭐
1. Acesse https://render.com e "Sign in with GitHub"
2. "New" → "Web Service" → conecte o repo **Ytld**
3. O `render.yaml` é detectado (plano free, Python 3.11)
4. Build: `pip install -r requirements.txt` | Start: gunicorn
5. URL: `https://<seu-app>.onrender.com`

### Koyeb (Free — generoso, sem cartão)
- Conecte GitHub e use o `Dockerfile` (Koyeb builda a imagem)

## Docker (local ou qualquer PaaS)
```
docker build -t yt-downloader .
docker run -p 5000:5000 -e PORT=5000 yt-downloader
```

## Variáveis de ambiente
- `PORT` — porta do servidor (usada automaticamente em PaaS)

## Não recomendados
- Fly.io (erro de machine state, free limitado)
- PythonAnywhere (bloqueia yt-dlp na rede)
- Netlify (não roda binários/executáveis)

## Estrutura
- `app.py` — backend Flask
- `templates/index.html` — interface web responsiva
- `requirements.txt` — dependências
- `Procfile` / `render.yaml` / `Dockerfile` — config de deploy

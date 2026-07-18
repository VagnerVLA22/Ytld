from flask import Flask, render_template, request, jsonify, Response, send_file
import subprocess
import re
import threading
import json
import time
import os
import tempfile
import shutil
import zipfile
import sys
import stat
from io import BytesIO

app = Flask(__name__)

# --- CONFIGURAÇÃO DE CAMINHO ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Pasta de binários (yt-dlp e ffmpeg baixados no startup em ambiente de deploy)
BIN_DIR = os.path.join(BASE_DIR, "bin")
os.makedirs(BIN_DIR, exist_ok=True)

# Em ambiente local Windows usamos os .exe da pasta; em deploy Linux usamos PATH ou /usr/local/bin
IS_WINDOWS = sys.platform.startswith("win")

def _find_exe(name, windows_name):
    if IS_WINDOWS:
        p = os.path.join(BASE_DIR, windows_name)
        return p if os.path.exists(p) else windows_name
    # Linux: procura no PATH, depois /usr/local/bin, depois BIN_DIR
    import shutil
    found = shutil.which(name)
    if found:
        return found
    for cand in [f"/usr/local/bin/{name}", os.path.join(BIN_DIR, name)]:
        if os.path.exists(cand):
            return cand
    return os.path.join(BIN_DIR, name)

YT_EXE = _find_exe("yt-dlp", "yt-dlp.exe")
FFMPEG_EXE = _find_exe("ffmpeg", "ffmpeg.exe")

# Pasta de downloads (em deploy usamos temp, local usamos Downloads\D0_youtube)
if IS_WINDOWS:
    DOWNLOADS_DIR = os.path.join(os.path.expanduser('~'), 'Downloads', 'D0_youtube')
else:
    DOWNLOADS_DIR = os.path.join(tempfile.gettempdir(), 'yt_downloads')
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

progress_status = "0"
last_downloaded_file = None
temp_dirs = []
current_playlist = []
playlist_data = None
is_playlist_download = False

# Em deploy (gunicorn), o bloco __main__ não roda, então baixamos os binários na importação
if not IS_WINDOWS:
    try:
        setup_binaries()
    except Exception as e:
        print(f"[SETUP] Falha ao preparar binários: {e}", file=sys.stderr)


def download_file(url, dest):
    """Baixa um arquivo binário usando requests (sem depender de curl/wget)."""
    import requests
    print(f"[SETUP] Baixando {url} -> {dest}", file=sys.stderr)
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(dest, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)


def setup_binaries():
    """Em ambiente Linux (deploy), baixa yt-dlp e ffmpeg estáticos se não existirem."""
    if IS_WINDOWS:
        if not os.path.exists(YT_EXE):
            print(f"ALERTA: {YT_EXE} não encontrado na pasta!", file=sys.stderr)
        return

    # yt-dlp (Linux)
    if not os.path.exists(YT_EXE):
        try:
            download_file("https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp", YT_EXE)
            os.chmod(YT_EXE, os.stat(YT_EXE).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
            print("[SETUP] yt-dlp baixado com sucesso.", file=sys.stderr)
        except Exception as e:
            print(f"[SETUP] Erro ao baixar yt-dlp: {e}", file=sys.stderr)
    else:
        # Garante permissão de execução mesmo se já existir
        try:
            os.chmod(YT_EXE, os.stat(YT_EXE).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        except:
            pass

    # ffmpeg: em Dockerfile já vem via apt; fora disso tentamos baixar estático
    if not os.path.exists(FFMPEG_EXE):
        try:
            ffmpeg_zip = os.path.join(BIN_DIR, "ffmpeg.zip")
            download_file("https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz", ffmpeg_zip)
            import tarfile
            with tarfile.open(ffmpeg_zip) as tar:
                for member in tar.getmembers():
                    if member.name.endswith("ffmpeg"):
                        member.name = "ffmpeg"
                        tar.extract(member, BIN_DIR)
            os.remove(ffmpeg_zip)
            os.chmod(FFMPEG_EXE, os.stat(FFMPEG_EXE).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
            print("[SETUP] ffmpeg baixado com sucesso.", file=sys.stderr)
        except Exception as e:
            print(f"[SETUP] ffmpeg não disponível (use Dockerfile ou instale via apt): {e}", file=sys.stderr)


def yt_cmd(*args):
    """Monta o comando yt-dlp como lista (sem shell=True, sem aspas manuais)."""
    cmd = [YT_EXE]
    if os.path.exists(FFMPEG_EXE):
        cmd.extend(['--ffmpeg-location', os.path.dirname(FFMPEG_EXE)])
    cmd.extend(args)
    return cmd


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/manifest.json')
def manifest():
    return send_file(os.path.join(BASE_DIR, 'templates', 'manifest.json'), mimetype='application/manifest+json')


@app.route('/sw.js')
def sw():
    # Serve o SW da pasta static (Flask já define content-type correto)
    return send_file(os.path.join(BASE_DIR, 'static', 'sw.js'), mimetype='application/javascript')


@app.route('/health')
def health():
    import shutil
    info = {
        'yt_exe': YT_EXE,
        'yt_exists': os.path.exists(YT_EXE),
        'yt_exec': os.access(YT_EXE, os.X_OK) if os.path.exists(YT_EXE) else False,
        'ffmpeg_exe': FFMPEG_EXE,
        'ffmpeg_exists': os.path.exists(FFMPEG_EXE),
        'is_windows': IS_WINDOWS,
        'python': shutil.which('python') or shutil.which('python3'),
    }
    return jsonify(info)


@app.route('/status')
def status():
    return jsonify({
        'progress': progress_status,
        'is_playlist': is_playlist_download,
        'has_file': bool(last_downloaded_file and os.path.exists(last_downloaded_file)),
        'file': os.path.basename(last_downloaded_file) if last_downloaded_file else None,
    })


@app.route('/analisar', methods=['POST'])
def analisar():
    if not os.path.exists(YT_EXE):
        return jsonify({'error': f'yt-dlp não encontrado em {YT_EXE}'}), 500

    url = request.json.get('url')
    print(f"[ANALISAR] URL: {url}", file=sys.stderr)
    print(f"[ANALISAR] YT_EXE={YT_EXE} existe={os.path.exists(YT_EXE)}", file=sys.stderr)
    print(f"[ANALISAR] FFMPEG_EXE={FFMPEG_EXE} existe={os.path.exists(FFMPEG_EXE)}", file=sys.stderr)

    if not url:
        return jsonify({'error': 'URL não fornecida'}), 400

    try:
        # Primeiro: tentar como playlist (--flat-playlist)
        cmd = yt_cmd('--flat-playlist', '-j', url)
        print(f"[ANALISAR] Como playlist: {' '.join(cmd)}", file=sys.stderr)

        res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=30)
        print(f"[ANALISAR] rc={res.returncode} stdout={res.stdout[:200]} stderr={res.stderr[:300]}", file=sys.stderr)

        if res.returncode != 0 or not res.stdout.strip():
            return jsonify({'error': f'yt-dlp falhou (rc={res.returncode}): {res.stderr[:500]}'}), 400

        lines = res.stdout.strip().split('\n')
        entries = []
        for line in lines:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except:
                    pass

        if len(entries) > 1:
            print(f"[ANALISAR] Playlist detectada: {len(entries)} vídeos", file=sys.stderr)
            videos = []
            for info in entries:
                vid = info.get('id', '')
                title = info.get('title', 'Sem título')
                videos.append({'id': vid, 'title': title, 'url': f"https://youtube.com/watch?v={vid}"})

            formats = []
            try:
                first_url = videos[0]['url']
                fmt_res = subprocess.run(yt_cmd('--no-playlist', '-j', first_url),
                                         capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=15)
                if fmt_res.returncode == 0 and fmt_res.stdout.strip():
                    first_info = json.loads(fmt_res.stdout)
                    for f in first_info.get('formats', []):
                        res_val = f.get('resolution') or f.get('format_note') or 'áudio'
                        size = f.get('filesize') or f.get('filesize_approx') or 0
                        size_mb = f"{size / (1024*1024):.1f}MB" if size > 0 else "?"
                        formats.append({'id': f['format_id'], 'label': f"[{f.get('ext','?')}] {res_val} ({size_mb})"})
            except Exception as e:
                print(f"[ANALISAR] Erro ao obter formatos do primeiro vídeo: {e}", file=sys.stderr)

            return jsonify({'type': 'playlist', 'count': len(videos), 'videos': videos, 'formats': formats[::-1]})

        info = entries[0] if entries else {}

    except Exception as e:
        print(f"[ANALISAR] Tentando como vídeo único: {e}", file=sys.stderr)
        try:
            res = subprocess.run(yt_cmd('--no-playlist', '-j', url),
                                 capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=30)
            print(f"[ANALISAR] video rc={res.returncode} stderr={res.stderr[:300]}", file=sys.stderr)

            if res.returncode != 0:
                return jsonify({'error': res.stderr or 'Erro ao analisar'}), 400

            info = json.loads(res.stdout)
        except Exception as e2:
            return jsonify({'error': f'Exceção: {str(e2)}'}), 500

    formats = []
    for f in info.get('formats', []):
        res_val = f.get('resolution') or f.get('format_note') or 'áudio'
        size = f.get('filesize') or f.get('filesize_approx') or 0
        size_mb = f"{size / (1024*1024):.1f}MB" if size > 0 else "?"
        formats.append({'id': f['format_id'], 'label': f"[{f.get('ext','?')}] {res_val} ({size_mb})"})

    return jsonify({'type': 'video', 'formats': formats[::-1]})


@app.route('/baixar', methods=['POST'])
def iniciar_download():
    global progress_status, last_downloaded_file, current_playlist, is_playlist_download
    data = request.json
    url = data['url']
    fid = data.get('fid')
    download_all = data.get('download_all', False)
    selected_indices = data.get('selected_indices')

    progress_status = "0.1"

    def run():
        global progress_status, last_downloaded_file, current_playlist, is_playlist_download

        if download_all and not fid:
            is_playlist_download = True
            temp_dir = tempfile.mkdtemp()
            temp_dirs.append(temp_dir)
            try:
                cmd = yt_cmd('--yes-playlist', '--newline', url,
                             '-o', f'{temp_dir}/%(playlist_index)s-%(title)s.%(ext)s')
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        text=True, encoding='utf-8', errors='ignore')
                for line in proc.stdout:
                    match = re.search(r'(\d+\.\d+)%', line)
                    if match:
                        progress_status = match.group(1)
                proc.wait()
                if proc.returncode == 0:
                    progress_status = "100"
                    files = sorted(os.listdir(temp_dir))
                    if files:
                        current_playlist = [os.path.join(temp_dir, f) for f in files]
                        last_downloaded_file = temp_dir
                    else:
                        progress_status = "error"
                else:
                    progress_status = "error"
            except Exception as e:
                print(f"Erro playlist: {e}", file=sys.stderr)
                progress_status = "error"

        elif download_all and fid:
            is_playlist_download = True
            temp_dir = tempfile.mkdtemp()
            temp_dirs.append(temp_dir)
            try:
                base_cmd = yt_cmd('--newline')

                if selected_indices:
                    playlist_items = ','.join(str(idx + 1) for idx in selected_indices)
                    base_cmd.extend(['--playlist-items', playlist_items])

                base_cmd.append('--yes-playlist')

                if fid.startswith("mp3-"):
                    bitrate = fid.split("-")[1]
                    base_cmd.extend(['-x', '--audio-format', 'mp3', '--audio-quality', bitrate])
                else:
                    base_cmd.extend(['-f', f'{fid}+bestaudio/best', '--recode-video', 'mp4'])

                base_cmd.extend([url, '-o', f'{temp_dir}/%(playlist_index)s-%(title)s.%(ext)s'])

                proc = subprocess.Popen(base_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        text=True, encoding='utf-8', errors='ignore')
                for line in proc.stdout:
                    match = re.search(r'(\d+\.\d+)%', line)
                    if match:
                        progress_status = match.group(1)
                proc.wait()
                if proc.returncode == 0:
                    progress_status = "100"
                    files = sorted(os.listdir(temp_dir))
                    if files:
                        current_playlist = [os.path.join(temp_dir, f) for f in files]
                        last_downloaded_file = temp_dir
                    else:
                        progress_status = "error"
                else:
                    progress_status = "error"
            except Exception as e:
                print(f"Erro playlist formato: {e}", file=sys.stderr)
                progress_status = "error"
        else:
            is_playlist_download = False
            temp_dir = tempfile.mkdtemp()
            temp_dirs.append(temp_dir)
            try:
                if fid and fid.startswith("mp3-"):
                    bitrate = fid.split("-")[1]
                    cmd = yt_cmd('-x', '--audio-format', 'mp3', '--audio-quality', bitrate,
                                 '--newline', url, '-o', f'{temp_dir}/%(title)s.%(ext)s')
                elif fid:
                    cmd = yt_cmd('-f', f'{fid}+bestaudio/best', '--recode-video', 'mp4',
                                 '--newline', url, '-o', f'{temp_dir}/%(title)s.%(ext)s')
                else:
                    cmd = yt_cmd('--newline', url, '-o', f'{temp_dir}/%(title)s.%(ext)s')
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        text=True, encoding='utf-8', errors='ignore')
                for line in proc.stdout:
                    match = re.search(r'(\d+\.\d+)%', line)
                    if match:
                        progress_status = match.group(1)
                proc.wait()
                if proc.returncode == 0:
                    progress_status = "100"
                    files = os.listdir(temp_dir)
                    if files:
                        last_downloaded_file = os.path.join(temp_dir, files[0])
                    else:
                        progress_status = "error"
                else:
                    progress_status = "error"
                    print(f"[DOWNLOAD] Falha rc={proc.returncode} cmd={' '.join(cmd)}", file=sys.stderr)
            except Exception as e:
                print(f"Erro download: {e}", file=sys.stderr)
                progress_status = "error"

    threading.Thread(target=run).start()
    return jsonify({"status": "started"})


@app.route('/progresso_feed')
def progresso_feed():
    def generate():
        while True:
            yield f"data: {progress_status}\n\n"
            if progress_status == "100":
                break
            time.sleep(0.5)
    return Response(generate(), mimetype='text/event-stream')


@app.route('/download_file')
def download_file():
    global last_downloaded_file, temp_dirs, current_playlist, is_playlist_download

    if is_playlist_download and current_playlist:
        memory_file = BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in current_playlist:
                if os.path.exists(file_path):
                    arcname = os.path.basename(file_path)
                    zipf.write(file_path, arcname)

        memory_file.seek(0)

        def cleanup():
            time.sleep(1)
            try:
                for temp_dir in temp_dirs:
                    if os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir)
                temp_dirs.clear()
            except:
                pass

        threading.Thread(target=cleanup).start()

        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name='playlist.zip'
        )

    elif last_downloaded_file and os.path.exists(last_downloaded_file):
        file_name = os.path.basename(last_downloaded_file)
        try:
            response = send_file(last_downloaded_file, as_attachment=True, download_name=file_name)
        except Exception as e:
            print(f"[DOWNLOAD_FILE] Erro send_file: {e}", file=sys.stderr)
            return jsonify({'error': f'Erro ao enviar arquivo: {e}'}), 500

        def cleanup():
            # Aguarda mais tempo para o send_file transmitir antes de apagar
            time.sleep(60)
            try:
                temp_dir = os.path.dirname(last_downloaded_file)
                if temp_dir in temp_dirs:
                    shutil.rmtree(temp_dir)
                    temp_dirs.remove(temp_dir)
                last_downloaded_file = None
            except:
                pass

        threading.Thread(target=cleanup).start()
        return response
    else:
        return jsonify({'error': 'Arquivo não encontrado'}), 404


if __name__ == '__main__':
    setup_binaries()

    import socket
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except:
        local_ip = "localhost"

    print("=========================================")
    print("YouTube Downloader está rodando!")
    print("=========================================")
    print(f"IP Local: http://{local_ip}:5000")
    print(f"Localhost: http://localhost:5000")
    print("=========================================")

    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

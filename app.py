from flask import Flask, request, jsonify, Response, send_from_directory
import yt_dlp
import os
import time
import uuid

app = Flask(__name__)
DOWNLOAD_DIR = os.path.join(os.getcwd(), 'downloads')
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
progress_state = {}

@app.route('/')
def serve_html():
    return send_from_directory('.', 'index.html')

@app.route('/download-progress')
def download_progress():
    links = request.args.get("links", "").split(',')
    format_type = request.args.get("format", "Video")
    filename_template = request.args.get("filename") or '%(title)s.%(ext)s'
    job_id = str(uuid.uuid4())
    progress_state[job_id] = 0

    def generate():
        def hook(d):
            if d['status'] == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate')
                downloaded = d.get('downloaded_bytes', 0)
                percent = int(downloaded / total * 100) if total else 0
                progress_state[job_id] = percent
            elif d['status'] == 'finished':
                progress_state[job_id] = 100

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(DOWNLOAD_DIR, filename_template),
            'quiet': True,
            'noplaylist': False,
            'ignoreerrors': True,
            'continuedl': True,
            'progress_hooks': [hook],
        }

        if format_type == "Audio":
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download(links)
        except Exception as e:
            print("Download failed:", str(e))

        for _ in range(101):
            yield f"data: {{\"percent\": {progress_state[job_id]}}}\n\n"
            if progress_state[job_id] >= 100:
                break
            time.sleep(0.5)

    return Response(generate(), mimetype='text/event-stream')

@app.route('/reset-progress', methods=['POST'])
def reset_progress():
    progress_state.clear()
    return jsonify({"status": "Progress reset"}), 200

@app.route('/downloads/<path:filename>')
def serve_download(filename):
    return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=True, threaded=True)

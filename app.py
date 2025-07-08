from flask import Flask, request, jsonify, Response, send_from_directory
import yt_dlp
import os
import time

app = Flask(__name__)
progress_state = {"percent": 0}

@app.route('/')
def serve_html():
    return send_from_directory('.', 'index.html')

@app.route('/download-progress')
def download_progress():
    links = request.args.get("links", "").split(',')
    format_type = request.args.get("format", "Video")
    folder = request.args.get("folder") or os.path.join(os.path.expanduser("~"), "Downloads")
    filename_template = request.args.get("filename") or '%(title)s.%(ext)s'

    os.makedirs(folder, exist_ok=True)

    def generate():
        def hook(d):
            if d['status'] == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate')
                downloaded = d.get('downloaded_bytes', 0)
                percent = int(downloaded / total * 100) if total else 0
                progress_state["percent"] = percent
            elif d['status'] == 'finished':
                progress_state["percent"] = 100

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(folder, filename_template),
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
            yield f"data: {{\"percent\": {progress_state['percent']}}}\n\n"
            if progress_state['percent'] >= 100:
                break
            time.sleep(0.5)

    return Response(generate(), mimetype='text/event-stream')

@app.route('/reset-progress', methods=['POST'])
def reset_progress():
    global progress_state
    progress_state = {"percent": 0}
    return jsonify({"status": "Progress reset"}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))  # Render uses dynamic PORT
    app.run(host='0.0.0.0', port=port, debug=True, threaded=True)

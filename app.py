from flask import Flask, render_template, request, send_file
import yt_dlp
import os
import shutil
import uuid

app = Flask(__name__)

DOWNLOAD_FOLDER = 'downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

app.config['DOWNLOAD_FOLDER'] = DOWNLOAD_FOLDER


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/download', methods=['POST'])
def download():
    url = request.form['url']

    session_id = str(uuid.uuid4())
    download_path = os.path.join(app.config['DOWNLOAD_FOLDER'], session_id)
    os.makedirs(download_path)

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            # If it's a playlist, the title will be in the info dictionary
            playlist_title = info.get('title', 'playlist')
            zip_filename = f"{playlist_title}.zip"
            zip_path = os.path.join(app.config['DOWNLOAD_FOLDER'], zip_filename)

            shutil.make_archive(os.path.join(app.config['DOWNLOAD_FOLDER'], playlist_title), 'zip', download_path)

            return send_file(zip_path, as_attachment=True)

    except yt_dlp.utils.DownloadError as e:
        return f"Error: {e}"
    finally:
        shutil.rmtree(download_path)


if __name__ == '__main__':
    app.run(debug=True)

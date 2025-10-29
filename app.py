from flask import Flask, render_template, request, send_file, after_this_request
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
        'ignoreerrors': True, # Continue downloading other videos in a playlist if one fails
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            playlist_title = info.get('title', 'playlist')
            # Sanitize the title to make it a valid filename
            sanitized_title = "".join([c for c in playlist_title if c.isalpha() or c.isdigit() or c in (' ', '-')]).rstrip()
            zip_filename_base = os.path.join(app.config['DOWNLOAD_FOLDER'], sanitized_title)

            # Create the zip file
            zip_path = shutil.make_archive(zip_filename_base, 'zip', download_path)

            @after_this_request
            def cleanup(response):
                try:
                    # Clean up the original temp folder
                    shutil.rmtree(download_path)
                    # Clean up the generated zip file
                    os.remove(zip_path)
                except Exception as e:
                    app.logger.error(f"Error during cleanup: {e}")
                return response

            return send_file(zip_path, as_attachment=True, download_name=f'{sanitized_title}.zip')

    except yt_dlp.utils.DownloadError as e:
        # If yt-dlp fails, ensure the temp directory is cleaned up
        shutil.rmtree(download_path)
        return f"Error during download: {e}"
    except Exception as e:
        # Handle other unexpected errors
        shutil.rmtree(download_path)
        return f"An unexpected error occurred: {e}"


if __name__ == '__main__':
    app.run(debug=True)

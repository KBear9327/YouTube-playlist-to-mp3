import os
import shutil
import yt_dlp
from redis import Redis
from rq import Worker, Queue

# --- Redis and RQ Setup ---
listen = ['default']
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
conn = Redis.from_url(redis_url)

# --- The Core Conversion Logic ---
def convert_playlist(url, job_id):
    """
    This function runs in the background to download, convert, and zip a playlist.
    """
    # Each job gets its own temporary directory for the mp3s
    temp_download_path = f"downloads/{job_id}"
    os.makedirs(temp_download_path, exist_ok=True)

    # Final zip file will be stored here, named after the job_id
    final_zip_path_base = f"downloads/{job_id}"

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(temp_download_path, '%(title)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'ignoreerrors': True, # Don't stop if one video in a playlist fails
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            playlist_title = info.get('title', 'playlist')
            # Sanitize title for the final zip filename the user will see
            sanitized_title = "".join([c for c in playlist_title if c.isalpha() or c.isdigit() or c in (' ', '-')]).rstrip()

        # Create the zip file from the downloaded mp3s
        shutil.make_archive(final_zip_path_base, 'zip', temp_download_path)

        # Return the sanitized title for use in the download link
        return sanitized_title

    finally:
        # Clean up the temporary directory with the individual mp3s
        if os.path.exists(temp_download_path):
            shutil.rmtree(temp_download_path)


# --- Start the Worker ---
if __name__ == '__main__':
    # The worker is instantiated with a connection directly,
    # avoiding the need for the Connection context manager.
    worker = Worker(map(Queue, listen), connection=conn)
    worker.work()

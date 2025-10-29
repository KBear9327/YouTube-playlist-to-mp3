import os
import uuid
from flask import Flask, render_template, request, redirect, url_for, send_file, after_this_request
from redis import Redis
from rq import Queue
from worker import convert_playlist # Import the conversion function

# --- App and Redis/RQ Setup ---
app = Flask(__name__)
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
conn = Redis.from_url(redis_url)
q = Queue(connection=conn)

# --- Ensure downloads directory exists ---
DOWNLOAD_FOLDER = 'downloads'
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
app.config['DOWNLOAD_FOLDER'] = DOWNLOAD_FOLDER

# --- Routes ---
@app.route('/')
def index():
    """Serves the main page with the URL input form."""
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert():
    """
    1. Receives a URL from the form.
    2. Creates a unique job ID.
    3. Enqueues the conversion task for the background worker.
    4. Redirects the user to the status page for that job.
    """
    url = request.form['url']
    if not url:
        return redirect(url_for('index'))

    job_id = str(uuid.uuid4())
    # Enqueue the job: function, args=(url, job_id), job_id itself
    q.enqueue(convert_playlist, url, job_id, job_id=job_id)

    return redirect(url_for('status', job_id=job_id))

@app.route('/status/<job_id>')
def status(job_id):
    """
    Displays the status of a conversion job.
    The page will auto-refresh to check for completion.
    """
    job = q.fetch_job(job_id)
    if job:
        return render_template('status.html', job=job)
    return "Job not found.", 404

@app.route('/download/<job_id>')
def download(job_id):
    """
    Provides the download link for the completed zip file.
    """
    job = q.fetch_job(job_id)
    if job and job.is_finished:
        # The worker returns the sanitized title of the playlist
        sanitized_title = job.result
        # The zip file is named after the job_id
        zip_path = os.path.join(app.config['DOWNLOAD_FOLDER'], f"{job_id}.zip")

        @after_this_request
        def cleanup(response):
            # Clean up the zip file after it has been sent
            try:
                os.remove(zip_path)
            except Exception as e:
                app.logger.error(f"Error cleaning up zip file: {e}")
            return response

        return send_file(zip_path, as_attachment=True, download_name=f"{sanitized_title}.zip")

    return "File not ready or does not exist.", 404

if __name__ == '__main__':
    app.run(debug=True)

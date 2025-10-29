import unittest
from unittest.mock import patch, MagicMock
from app import app, q # Import the app and the queue
import os
import shutil

class AppArchitectureTestCase(unittest.TestCase):

    def setUp(self):
        """Set up a test client and configure the app for testing."""
        app.config['TESTING'] = True
        self.client = app.test_client()
        self.test_download_folder = 'test_downloads'
        app.config['DOWNLOAD_FOLDER'] = self.test_download_folder

        # Ensure the test directory is clean before each test
        if os.path.exists(self.test_download_folder):
            shutil.rmtree(self.test_download_folder)
        os.makedirs(self.test_download_folder)

    def tearDown(self):
        """Clean up the test directory after each test."""
        if os.path.exists(self.test_download_folder):
            shutil.rmtree(self.test_download_folder)

    def test_index_page(self):
        """Test that the index page loads correctly."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'YouTube to MP3 Converter', response.data)

    @patch('app.q.enqueue')
    @patch('app.uuid.uuid4')
    def test_convert_enqueues_job_and_redirects(self, mock_uuid, mock_enqueue):
        """Test that the /convert route enqueues a job and redirects to the status page."""
        mock_uuid.return_value = 'test-job-id'

        response = self.client.post('/convert', data={'url': 'https://a.test.url/playlist'})

        # Check that a job was enqueued with the correct arguments
        mock_enqueue.assert_called_once()
        self.assertEqual(mock_enqueue.call_args[0][1], 'https://a.test.url/playlist') # url
        self.assertEqual(mock_enqueue.call_args[0][2], 'test-job-id') # job_id
        self.assertEqual(mock_enqueue.call_args[1]['job_id'], 'test-job-id') # job_id kwarg

        # Check that the response is a redirect to the correct status page
        self.assertEqual(response.status_code, 302)
        self.assertIn('/status/test-job-id', response.location)

    @patch('app.q.fetch_job')
    def test_status_page_for_finished_job(self, mock_fetch_job):
        """Test the status page when a job is successfully finished."""
        mock_job = MagicMock()
        mock_job.id = 'finished-job-id'
        mock_job.is_finished = True
        mock_job.is_failed = False
        mock_job.get_status.return_value = 'finished'

        mock_fetch_job.return_value = mock_job

        response = self.client.get('/status/finished-job-id')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Conversion Complete!', response.data)
        self.assertIn(b'Download MP3 Playlist', response.data)
        self.assertIn(b'/download/finished-job-id', response.data)

    @patch('app.q.fetch_job')
    def test_download_route(self, mock_fetch_job):
        """Test the download route for a completed job."""
        # --- Mock Setup ---
        mock_job = MagicMock()
        mock_job.id = 'download-job-id'
        mock_job.is_finished = True
        # The worker returns the sanitized title as the job result
        mock_job.result = 'Test Playlist Title'
        mock_fetch_job.return_value = mock_job

        # --- File Setup ---
        # The application expects a zip file named after the job_id
        zip_path = os.path.join(self.test_download_folder, 'download-job-id.zip')
        with open(zip_path, 'w') as f:
            f.write('dummy zip content')
        self.assertTrue(os.path.exists(zip_path))

        # --- Request and Assertions ---
        response = self.client.get('/download/download-job-id')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'application/zip')
        # Check that the response headers suggest the correct filename for the user
        self.assertIn('attachment; filename="Test Playlist Title.zip"', response.headers['Content-Disposition'])

        # After the request, the cleanup function should have deleted the file
        self.assertFalse(os.path.exists(zip_path))


if __name__ == '__main__':
    unittest.main()

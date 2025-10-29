import unittest
from unittest.mock import patch, MagicMock
from app import app
import os
import shutil
import uuid

class AppTestCase(unittest.TestCase):

    def setUp(self):
        """Set up a test client and other test variables."""
        app.config['TESTING'] = True
        self.client = app.test_client()
        self.test_download_folder = 'test_downloads'
        app.config['DOWNLOAD_FOLDER'] = self.test_download_folder
        # Start with a clean directory for each test
        if os.path.exists(self.test_download_folder):
            shutil.rmtree(self.test_download_folder)
        os.makedirs(self.test_download_folder)

    def tearDown(self):
        """Clean up the test downloads directory."""
        if os.path.exists(self.test_download_folder):
            shutil.rmtree(self.test_download_folder)

    def test_index(self):
        """Test that the index page loads correctly."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'YouTube to MP3 Converter', response.data)

    @patch('app.yt_dlp.YoutubeDL')
    @patch('app.uuid.uuid4')
    def test_download_success_and_cleanup(self, mock_uuid, mock_youtube_dl):
        """Test the download functionality and cleanup with a mocked yt-dlp."""
        # --- Mock setup ---
        mock_uuid.return_value = 'test-session-id'
        session_path = os.path.join(self.test_download_folder, 'test-session-id')

        # This side effect function simulates yt-dlp creating files.
        # It runs when `extract_info` is called in the application code.
        def mock_extract_info_side_effect(url, download=True):
            # By the time this runs, the app should have created the session directory.
            # We will create the dummy files inside it to simulate a download.
            os.makedirs(os.path.join(session_path, "."), exist_ok=True) # Ensure dir exists
            with open(os.path.join(session_path, 'test1.mp3'), 'w') as f:
                f.write('dummy audio content')
            # Return the metadata the app needs to proceed.
            return {'title': 'Test Playlist'}

        mock_ydl_instance = MagicMock()
        mock_ydl_instance.extract_info.side_effect = mock_extract_info_side_effect
        mock_youtube_dl.return_value.__enter__.return_value = mock_ydl_instance

        # --- Trigger the request ---
        response = self.client.post('/download', data={'url': 'https://www.youtube.com/playlist?list=TEST'})

        # --- Assertions ---
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'application/zip')
        self.assertIn('attachment; filename="Test Playlist.zip"', response.headers['Content-Disposition'])

        # Check that the temporary files and the zip file are cleaned up after the request.
        # Note: The cleanup happens *after* the response is sent, so we check the file system state after the call.
        zip_path = os.path.join(self.test_download_folder, 'Test Playlist.zip')
        self.assertFalse(os.path.exists(zip_path), "Zip file should have been deleted.")
        self.assertFalse(os.path.exists(session_path), "Temporary session directory should have been deleted.")

if __name__ == '__main__':
    unittest.main()

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.clock import Clock
from jnius import autoclass
import yt_dlp
import threading
import os

# Get the public downloads directory on Android
Environment = autoclass('android.os.Environment')
download_dir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS).getAbsolutePath()

class YouTubeDownloader(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 10
        self.spacing = 10

        self.add_widget(Label(text='YouTube to MP3 Converter'))
        self.url_input = TextInput(hint_text='Enter YouTube URL')
        self.add_widget(self.url_input)
        self.download_button = Button(text='Download')
        self.download_button.bind(on_press=self.start_download_thread)
        self.add_widget(self.download_button)
        self.status_label = Label(text='')
        self.add_widget(self.status_label)

    def update_status(self, text):
        def update_label(dt):
            self.status_label.text = text
        Clock.schedule_once(update_label)

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes') or 0
            downloaded_bytes = d.get('downloaded_bytes') or 0
            if total_bytes > 0:
                percent = downloaded_bytes / total_bytes * 100
                self.update_status(f"Downloading: {d['filename']} - {percent:.2f}%")
        elif d['status'] == 'finished':
            self.update_status('Download finished, converting...')

    def start_download_thread(self, instance):
        self.update_status('Starting download...')
        thread = threading.Thread(target=self.download_video)
        thread.start()

    def download_video(self):
        url = self.url_input.text
        if not url:
            self.update_status('Please enter a URL')
            return

        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': os.path.join(download_dir, '%(title)s.%(ext)s'),
            'progress_hooks': [self.progress_hook],
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            self.update_status('Download complete!')
        except Exception as e:
            self.update_status(f'Error: {e}')

class MainApp(App):
    def build(self):
        return YouTubeDownloader()

if __name__ == '__main__':
    MainApp().run()

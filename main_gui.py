from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
import os
import threading

# Import the core processing function
try:
    from music_tagger import process_single_file
except Exception:
    process_single_file = None


class MainUI(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=10, spacing=10, **kwargs)

        self.add_widget(Label(text='Music-Tagger (Kivy GUI - Minimal)', size_hint_y=None, height=40))

        grid = GridLayout(cols=2, size_hint_y=None, height=200, row_default_height=40, row_force_default=True)

        grid.add_widget(Label(text='File path:'))
        self.file_input = TextInput(text='', multiline=False)
        grid.add_widget(self.file_input)

        grid.add_widget(Label(text='Artist:'))
        self.artist_input = TextInput(text='', multiline=False)
        grid.add_widget(self.artist_input)

        grid.add_widget(Label(text='Title:'))
        self.title_input = TextInput(text='', multiline=False)
        grid.add_widget(self.title_input)

        grid.add_widget(Label(text='Dry run:'))
        self.dry_check = CheckBox(active=True)
        grid.add_widget(self.dry_check)

        self.add_widget(grid)

        run_btn = Button(text='Run (dry-run)', size_hint_y=None, height=44)
        run_btn.bind(on_release=self.on_run)
        self.add_widget(run_btn)

        self.output = Label(text='输出将显示在此处', valign='top')
        scroll = ScrollView()
        scroll.add_widget(self.output)
        self.add_widget(scroll)

    def on_run(self, *args):
        file_path = self.file_input.text.strip()
        artist = self.artist_input.text.strip()
        title = self.title_input.text.strip()
        dry = self.dry_check.active

        if not file_path or not os.path.isfile(file_path):
            self.output.text = '错误：请选择有效的音频文件路径。'
            return
        if not artist or not title:
            self.output.text = '错误：请填写 Artist 与 Title。'
            return

        # Run processing in a thread to avoid blocking UI
        threading.Thread(target=self._run_processing, args=(file_path, artist, title, dry), daemon=True).start()

    def _run_processing(self, file_path, artist, title, dry):
        config = {
            'clean_noise': True,
            'rename_files': False,
            'clear_tags': False,
            'use_network': False,
            'dry_run': dry
        }

        if process_single_file is None:
            self.output.text = '无法导入 music_tagger.process_single_file，请确保 music_tagger.py 在同一目录并可导入。'
            return

        # Call the core function and capture printed output by redirecting stdout would be better,
        # but to keep this minimal we will run and then show a simple success/failure message.
        try:
            ok = process_single_file(file_path, os.path.basename(file_path), artist, title, config)
            self.output.text = '处理完成: 成功' if ok else '处理完成: 失败 (请查看 Action/日志以获得详细信息)'
        except Exception as e:
            self.output.text = f'运行时异常: {e}'


class MusicTaggerApp(App):
    def build(self):
        return MainUI()


if __name__ == '__main__':
    MusicTaggerApp().run()


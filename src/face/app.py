import sys, io
import toga
from toga.style import Pack
from toga.style.pack import COLUMN, CENTER

class EyelidApp(toga.App):
    def startup(self):
        self.main_window = toga.MainWindow(title=self.formal_name)
        self.image_view = toga.ImageView(style=Pack(flex=1))
        self.lbl_ecr = toga.Label("ECR: --")
        self.lbl_blg = toga.Label("BLG: --")
        self.lbl_mar = toga.Label("MAR: --")

        box = toga.Box(
            children=[self.image_view, self.lbl_ecr, self.lbl_blg, self.lbl_mar],
            style=Pack(direction=COLUMN, alignment=CENTER)
        )
        self.main_window.content = box
        self.main_window.show()

        # プラットフォームでバックエンド切替
        if sys.platform == "ios":
            from .backend_ios import EyelidEngine
        else:
            from .backend_cv import EyelidEngine

        self.engine = EyelidEngine()
        self._latest = None

        def on_frame(frame_bytes, ecr, blg, mar):
            self._latest = (frame_bytes, ecr, blg, mar)
        self.engine.start(on_frame)

        # 20ms ≈ 50 FPS でUI更新
        self.timer = toga.Timer(0.02, self._tick, repeat=True)
        self.timer.start()

    def _tick(self, *_):
        if self._latest:
            frame_bytes, ecr, blg, mar = self._latest
            self.image_view.image = toga.Image(data=io.BytesIO(frame_bytes))
            self.lbl_ecr.text = f"ECR: {ecr:.2f}"
            self.lbl_blg.text = f"BLG: {blg:.0f}"
            self.lbl_mar.text = f"MAR: {mar:.2f}"

    def on_exit(self):
        if hasattr(self, "timer") and self.timer:
            self.timer.stop()
        if hasattr(self, "engine") and self.engine:
            self.engine.stop()

def main():
    # pyproject.toml の bundle/dev.kato と app名 face に合わせる
    return EyelidApp("face", "dev.kato.face")

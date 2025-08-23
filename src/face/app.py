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

        # alignment(非推奨) → align_items に変更
        box = toga.Box(
            children=[self.image_view, self.lbl_ecr, self.lbl_blg, self.lbl_mar],
            style=Pack(direction=COLUMN, align_items=CENTER)
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

        # バックエンドからのフレーム受け取りコールバック
        def on_frame(frame_bytes, ecr, blg, mar):
            self._latest = (frame_bytes, ecr, blg, mar)
        self.engine.start(on_frame)

        # 初回のUI更新をスケジュール（以後は _tick 内で再スケジュール）
        self.loop.call_soon(self._tick)

    def _tick(self):
        # 最新フレームがあればUIを更新
        if self._latest:
            frame_bytes, ecr, blg, mar = self._latest
            self.image_view.image = toga.Image(data=io.BytesIO(frame_bytes))
            self.lbl_ecr.text = f"ECR: {ecr:.2f}"
            self.lbl_blg.text = f"BLG: {blg:.0f}"
            self.lbl_mar.text = f"MAR: {mar:.2f}"

        # 20ms ≈ 50 FPS で次の更新をスケジュール
        self.loop.call_later(0.02, self._tick)

    def on_exit(self):
        if hasattr(self, "engine") and self.engine:
            self.engine.stop()

def main():
    # pyproject.toml に合わせて app_id を設定
    return EyelidApp("face", "dev.kato.face")

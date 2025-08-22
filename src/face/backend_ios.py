import threading, time, base64

# 1x1の黒PNG（カメラ非対応のiOSシミュレーター用プレースホルダー）
_BLACK_PNG = base64.b64decode(
    b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMBAFZp6i0AAAAASUVORK5CYII="
)

class EyelidEngine:
    def __init__(self):
        self._stop = threading.Event()
        self._th = None

    def start(self, callback):
        def loop():
            while not self._stop.is_set():
                callback(_BLACK_PNG, 0.0, 0.0, 0.0)
                time.sleep(0.2)
        self._th = threading.Thread(target=loop, daemon=True)
        self._stop.clear()
        self._th.start()

    def stop(self):
        self._stop.set()
        if self._th:
            self._th.join(timeout=1.0)

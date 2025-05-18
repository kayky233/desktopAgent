# observer.py
import io, base64, time, pyautogui as pag
from dataclasses import dataclass

@dataclass
class Observation:
    img_b64: str | None
    window_title: str

    @classmethod
    def capture(cls):
        buf = io.BytesIO()
        pag.screenshot().save(buf, "PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        title = pag.getActiveWindowTitle() or ""
        return cls(img_b64=b64, window_title=title)

    # Vision 消息
    def as_vision_message(self, caption: str = ""):
        return {
            "role": "user",
            "content": [
                {"type": "text", "text": caption},
                {"type": "image_url",
                 "image_url": {"url": f"data:image/png;base64,{self.img_b64}"}}
            ]
        }

    # Text 摘要
    def as_text_message(self):
        t = time.strftime('%H:%M:%S')
        return {"role": "user",
                "content": f"[{t}] active window: {self.window_title}"}

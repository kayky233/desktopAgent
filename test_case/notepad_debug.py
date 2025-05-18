from pywinauto import Desktop
import time


def debug_notepad():
    d = Desktop(backend="win32")

    print("所有记事本窗口:")
    notepads = [w for w in d.windows() if w.class_name() == "Notepad"]

    if not notepads:
        print("没有找到记事本窗口")
        return

    for i, w in enumerate(notepads):
        try:
            print(f"{i + 1}. 标题: '{w.window_text()}' | 矩形: {w.rectangle()}")
            w.set_focus()
            time.sleep(1)
        except Exception as e:
            print(f"无法访问窗口: {e}")


if __name__ == "__main__":
    debug_notepad()
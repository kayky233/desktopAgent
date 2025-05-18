# debug_windows.py
from pywinauto import Desktop


def list_windows():
    desktop = Desktop(backend="uia")
    print("UIA 后端找到的窗口:")
    for i, w in enumerate(desktop.windows()):
        try:
            print(f"{i + 1}. {w.window_text()} | {w.class_name()} | {w.process_name()}")
        except:
            print(f"{i + 1}. [无法获取信息]")

    desktop = Desktop(backend="win32")
    print("\nWin32 后端找到的窗口:")
    for i, w in enumerate(desktop.windows()):
        try:
            print(f"{i + 1}. {w.window_text()} | {w.class_name()}")
        except:
            print(f"{i + 1}. [无法获取信息]")


if __name__ == "__main__":
    list_windows()
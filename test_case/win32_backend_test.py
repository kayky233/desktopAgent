from pywinauto import Desktop
d = Desktop(backend="win32")
for w in d.windows(class_name="Notepad"):
    print(w.window_text())
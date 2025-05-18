import time
import pyautogui as pag
from pywinauto import Desktop, Application
from tenacity import retry, stop_after_attempt, wait_fixed
import psutil
import subprocess

pag.FAILSAFE = True
ALLOWED_HOTKEYS = [["ctrl", "s"], ["ctrl", "o"], ["alt", "f4"]]


class Executor:
    def __init__(self):
        # 强制使用win32后端
        self.backend = "win32"
        self.desktop = Desktop(backend=self.backend)
        self.app = Application(backend=self.backend)

    def _find_window(self, title=None, class_name=None, process_name=None, ctrl_kw=None):
        """专为Win32后端优化的窗口查找"""
        try:
            # 优先使用类名查找
            if class_name:
                windows = []
                for w in self.desktop.windows(class_name=class_name):
                    try:
                        if not title or (w.window_text() and title in w.window_text()):
                            windows.append(w)
                    except:
                        continue

                if windows:
                    if ctrl_kw:
                        return windows[0][ctrl_kw]
                    return windows[0]

            # 回退到标题查找
            if title:
                for w in self.desktop.windows():
                    try:
                        if title in w.window_text():
                            if ctrl_kw:
                                return w[ctrl_kw]
                            return w
                    except:
                        continue

        except Exception as e:
            print(f"窗口查找出错: {e}")

        raise RuntimeError(f"未找到匹配窗口（title={title}, class={class_name}）")

    def focus_window(self, title=None, class_name=None, process_name=None):
        """改进的窗口聚焦方法"""
        # 特殊处理记事本窗口
        if class_name == "Notepad" or (process_name and "notepad" in process_name.lower()):
            self._ensure_notepad_focus()
            return

        self._find_window(title=title, class_name=class_name, process_name=process_name).set_focus()

    def _ensure_notepad_focus(self):
        """专门处理记事本窗口聚焦"""
        try:
            # 尝试连接已存在的记事本
            try:
                app = self.app.connect(class_name="Notepad")
                app.window(class_name="Notepad").set_focus()
                return
            except:
                pass

            # 如果没有找到，则启动新的记事本
            subprocess.Popen(r"C:\Windows\System32\notepad.exe")
            time.sleep(2)
            self.app.connect(class_name="Notepad").window(class_name="Notepad").set_focus()
        except Exception as e:
            raise RuntimeError(f"无法聚焦记事本窗口: {e}")

    def click_ctrl(self, title, ctrl):
        self._find_window(title=title, ctrl_kw=ctrl).click_input()

    def move(self, x, y):
        pag.moveTo(x, y)

    def click(self, x=None, y=None, button='left', retry=3):
        """更健壮的点击方法"""
        for _ in range(retry):
            try:
                if x is None or y is None:
                    x, y = pag.position()
                    print(f"将在当前位置点击: ({x}, {y})")

                pag.click(x, y, button=button)
                return True
            except Exception as e:
                print(f"点击失败: {e}")
                time.sleep(1)
        return False

    def click_image(self, img, conf=0.9):
        pos = pag.locateCenterOnScreen(img, confidence=conf)
        if not pos:
            raise RuntimeError(f"图像 {img} 未匹配")
        pag.click(pos)

    def type_text(self, txt):
        pag.write(txt, interval=0.05)

    def hotkey(self, *keys):
        pag.hotkey(*keys)

    def sleep(self, sec):
        time.sleep(sec)

    def input_text(self, text):
        self.type_text(text)

    def debug_save_dialog():
        """调试保存对话框"""
        try:
            dlg = Desktop(backend="win32").window(title="另存为")
            print("找到保存对话框:")
            print(f"标题: {dlg.window_text()}")
            print("所有控件标识:")
            dlg.print_control_identifiers()

            # 尝试定位保存按钮
            try:
                btn = dlg.Button("保存(&S)")
                print(f"找到保存按钮: {btn}")
            except:
                print("未找到标准保存按钮，尝试其他定位方式")
                try:
                    btn = dlg.Save
                    print(f"找到Save按钮: {btn}")
                except:
                    print("未找到任何保存按钮")

            return True
        except Exception as e:
            print(f"未找到保存对话框: {e}")
            return False

    def save_file(self, path):
        """精准保存优化版（仅优化最后点击步骤）"""
        try:
            path_str = str(path)

            # 1. 触发保存快捷键（保持不变）
            pag.hotkey('ctrl', 's')
            time.sleep(2)

            # 2. 输入路径（保持不变）
            pag.write(path_str)
            time.sleep(1)

            # 3. 终极保存点击方案（新增部分）
            for _ in range(3):  # 最多尝试3次
                try:
                    # 方案1：尝试通过pywinauto点击保存按钮
                    dlg = self.app.window(title="另存为", class_name="#32770")
                    save_btn = dlg.child_window(title="保存", control_type="Button")
                    save_btn.click()
                    time.sleep(1)
                    break
                except:
                    # 方案2：直接键盘回车（保底）
                    pag.press('enter')
                    time.sleep(1)

            # 4. 处理可能的覆盖确认
            try:
                confirm_dlg = self.app.window(title="确认另存为", timeout=1)
                confirm_dlg.child_window(title="是", control_type="Button").click()
            except:
                pass

        except Exception as e:
            raise RuntimeError(f"保存失败: {e}")

        # 5. 添加视觉反馈（调试用）
        pag.moveRel(10, 10)  # 小幅度移动鼠标，可见操作完成

    def debug_mouse_position(self):
        """调试用：显示当前鼠标位置"""
        try:
            x, y = pag.position()
            print(f"当前鼠标位置: ({x}, {y})")
            return x, y
        except Exception as e:
            print(f"获取鼠标位置失败: {e}")
            return None, None

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    def dispatch(self, cmd: dict):
        act, a = cmd["action"], cmd.get("args", {})
        try:
            print(f"执行命令: {cmd}")  # 调试日志

            match act:
                case "focus_window":
                    self.focus_window(
                        a.get("title"),
                        a.get("class_name"),
                        a.get("process_name")
                    )
                case "click_ctrl":
                    self.click_ctrl(a["title"], a["ctrl"])
                case "click":
                    print(f"点击位置: x={a.get('x')}, y={a.get('y')}")
                    if a.get("x") is None or a.get("y") is None:
                        self.debug_mouse_position()
                    # 处理可能缺少坐标的情况
                    x = a.get("x")
                    y = a.get("y")
                    button = a.get("button", "left")
                    self.click(x, y, button=button)
                case "click_img":
                    self.click_image(a["img"], a.get("conf", 0.9))
                case "move":
                    self.move(a["x"], a["y"])
                case "type":
                    self.type_text(a["text"])
                case "hotkey":
                    # 处理两种热键格式：
                    # 1. {'keys': ['Ctrl', 'S']}
                    # 2. {'key': 'Ctrl+S'}
                    if "keys" in a:
                        keys = a["keys"]
                    elif "key" in a:
                        keys = a["key"].split("+")
                    else:
                        raise ValueError("热键动作缺少keys或key参数")

                    if not isinstance(keys, list):
                        keys = [keys]

                    # 统一转为小写比较
                    lower_keys = [k.lower() for k in keys]
                    allowed_str = ", ".join("+".join(hk) for hk in ALLOWED_HOTKEYS)

                    if lower_keys not in ALLOWED_HOTKEYS:
                        raise ValueError(
                            f"热键 {'+'.join(keys)} 不在允许列表中\n"
                            f"允许的热键: {allowed_str}"
                        )
                    self.hotkey(*keys)
                case "sleep":
                    self.sleep(a.get("sec", 1))
                case "input_text":
                    self.input_text(a["text"])
                case "save_file":
                    self.save_file(a["path"])
                case "finish":
                    return "FINISH"
                case _:
                    raise ValueError(f"未知动作: {act}")
            return "OK"
        except KeyError as e:
            raise ValueError(f"缺少必要参数: {e}") from e
        except Exception as e:
            print(f"执行动作 {act} 失败: {e}")
            raise
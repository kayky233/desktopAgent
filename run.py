# run.py
import argparse, subprocess, time, os
from flow_manager import FlowManager
from executor import Executor
from pywinauto import Desktop
from pywinauto import Desktop,Application
import psutil
from pathlib import Path


def verify_and_retry_save(path, max_retry=3):
    """验证保存结果并重试"""
    path = Path(path)  # 确保是Path对象
    path_str = str(path)  # 字符串版本用于打印

    for attempt in range(max_retry):
        if path.exists():
            print(f"✓ 文件已成功保存到: {path_str}")
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    print(f"文件内容: {f.read()}")
                return True
            except Exception as e:
                print(f"文件读取错误: {e}")

        print(f"尝试 {attempt + 1}/{max_retry}: 文件未保存，重新尝试保存...")
        try:
            executor.save_file(path_str)  # 传入字符串
            time.sleep(2)
        except Exception as e:
            print(f"保存失败: {e}")

    print(f"✗ 保存失败，文件未创建: {path_str}")
    return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode",   choices=["vision","text"], default="vision")
    parser.add_argument("--vendor", choices=["openai","azure","deepseek","hf_local"],
                        default="openai")
    parser.add_argument("--model",  help="模型名或部署名", default="gpt-4o-mini")
    parser.add_argument("--endpoint", help="自定义 endpoint(base_url)", default=None)
    parser.add_argument("--api_key",  help="API Key(可用环境变量代替)", default=None)
    args = parser.parse_args()

    provider_kw = {}
    # 先找 key：CLI > OPENAI_API_KEY > DEEPSEEK_KEY
    args.api_key = (os.getenv("DEEPSEEK_KEY"))
    if args.vendor in ("azure", "hf_local", "deepseek"):
        if args.endpoint:  provider_kw["endpoint"] = args.endpoint
    if args.api_key: provider_kw["api_key"] = args.api_key
    print("DEBUG  DEEPSEEK_KEY  =", args.api_key)
    if args.vendor == "azure":
        provider_kw["deployment"] = args.model
    elif args.vendor == "deepseek":
        provider_kw["base_url"] = args.endpoint
        if args.api_key:
            provider_kw["api_key"] = args.api_key
        else:
            raise ValueError("DeepSeek 需要 --api_key 或环境变量 OPENAI_API_KEY/DEEPSEEK_KEY")

    # 在启动流程部分修改为：
    executor = Executor()

    # 不再需要单独启动记事本，由executor自动处理
    executor.focus_window(class_name="Notepad")

    # 在运行前添加
    # 获取桌面路径并确保目录存在
    DESKTOP = Path.home() / "Desktop"
    DESKTOP.mkdir(exist_ok=True)  # 确保桌面目录存在
    SAVE_PATH = DESKTOP / "demo.txt"

    # 如果文件已存在则删除
    if SAVE_PATH.exists():
        os.remove(SAVE_PATH)

    print(f"文件将保存到: {SAVE_PATH}")

    # 修改目标设置
    goal = f"在记事本写入 'Unified interface demo' 并保存到 {SAVE_PATH}"
    FlowManager(goal,
                mode=args.mode,
                vendor=args.vendor,
                model=args.model,
                provider_kwargs=provider_kw).run()
    verify_and_retry_save(SAVE_PATH)


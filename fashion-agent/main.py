# -*- coding: utf-8 -*-
"""main.py —— 一键启动 Web 界面（等价于 streamlit run src/web/app.py）"""

import os
import subprocess
import sys

if __name__ == "__main__":
    # 保证在项目根目录运行（config 用 BASE_DIR 定位路径，不依赖当前目录）
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print("🚀 启动 服装趋势分析 Agent ...")
    print("   浏览器将自动打开 http://localhost:8501")
    subprocess.run([sys.executable, "-m", "streamlit", "run", "src/web/app.py"])

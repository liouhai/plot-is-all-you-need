#!/usr/bin/env python3
"""旧脚本名的兼容入口；下载和拆图已分别迁移到 download.py 与 extract.py。"""
from main_entry import main

if __name__ == "__main__":
    raise SystemExit(main())

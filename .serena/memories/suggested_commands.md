Windows 常用命令：Get-ChildItem 查看目录，Get-Content 读文件，rg -n 搜索文本。
项目运行相关：python main.py 启动应用（main.py 调用 uvicorn.run）。
测试相关：优先尝试 python -m pytest tests -q；如果环境使用 uv，则尝试 uv run pytest tests -q。当前环境中直接 pytest 命令不可用。
数据库相关：Alembic 已配置，迁移位于 alembic/versions。
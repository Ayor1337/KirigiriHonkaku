"""运行时文件存储实现。"""

from pathlib import Path


class FileStorage:
    """负责会话运行时目录的初始化与文件读写。"""

    SESSION_SUBDIRS = ("story", "history", "truth", "npc", "dialogue", "clue")

    def __init__(self, root: Path):
        self.root = root

    def initialize(self) -> None:
        """初始化运行时根目录。"""

        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "sessions").mkdir(parents=True, exist_ok=True)

    def create_session_tree(self, session_uuid: str) -> dict[str, str]:
        """为会话创建标准目录树并返回路径映射。"""

        session_root = self.root / "sessions" / session_uuid
        session_root.mkdir(parents=True, exist_ok=True)
        directories = {"session_root": str(session_root)}
        for subdir in self.SESSION_SUBDIRS:
            path = session_root / subdir
            path.mkdir(parents=True, exist_ok=True)
            directories[subdir] = str(path)
        return directories

    def write_session_file(self, session_uuid: str, category: str, filename: str, content: str) -> str:
        """向会话目录下的指定类别写入文本文件。"""

        target_dir = self.root / "sessions" / session_uuid / category
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / filename
        target.write_text(content, encoding="utf-8")
        return str(target)

    def write_session_history(self, session_uuid: str, filename: str, content: str) -> str:
        """向会话历史目录写入动作结果文件。"""

        return self.write_session_file(session_uuid, "history", filename, content)

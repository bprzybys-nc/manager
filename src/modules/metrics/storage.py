from pathlib import Path
from typing import Optional


class Storage:
    def __init__(self, metrics_dir: str = "metrics"):
        self.metrics_dir = Path(metrics_dir)
        self.metrics_dir.mkdir(exist_ok=True)

    def store(self, instance_id: str, content: str) -> None:
        self._get_metrics_path(instance_id).write_text(content)

    def retrieve(self, instance_id: str) -> Optional[str]:
        path = self._get_metrics_path(instance_id)
        try:
            return path.read_text()
        except FileNotFoundError:
            return None

    def _get_metrics_path(self, instance_id: str) -> Path:
        return self.metrics_dir / instance_id

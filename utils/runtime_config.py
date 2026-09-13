"""Keep machine settings and UI configuration writes out of tracked files."""
from pathlib import Path
import shutil


def get_config_path():
    local_path = Path('config/config.local.ini')
    if not local_path.exists():
        shutil.copyfile('config/config.ini', local_path)
        local_path.chmod(0o600)
    return str(local_path)

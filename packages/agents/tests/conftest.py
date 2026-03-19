import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))
repo_root = root.parents[1]
for _ in range(5):
    if (repo_root / "foundry.toml").exists() or (repo_root / ".env.example").exists():
        break
    repo_root = repo_root.parent

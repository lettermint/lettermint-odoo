"""Create installable modules for one supported Odoo version."""

import ast
import pprint
import shutil
import sys
from pathlib import Path

version = sys.argv[1] if len(sys.argv) > 1 else "19"
if version not in ("18", "19"):
    raise SystemExit("Use version 18 or 19.")
root = Path(__file__).resolve().parents[1]
output = root / ".build" / version
output.mkdir(parents=True, exist_ok=True)
for name in ("lettermint_mail", "lettermint_mass_mailing"):
    target = output / name
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(root / name, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    manifest_file = target / "__manifest__.py"
    manifest = ast.literal_eval(manifest_file.read_text())
    manifest["version"] = version + ".0." + ".".join(manifest["version"].split(".")[2:])
    manifest_file.write_text(pprint.pformat(manifest, sort_dicts=False) + "\n")
print(output)

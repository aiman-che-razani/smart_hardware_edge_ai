"""Best-effort live snapshot; readers/antivirus can transiently lock Windows files."""
import json
import logging
from pathlib import Path


def publish(root, value):
    temporary=Path(root)/"status.partial"
    try:
        temporary.write_text(json.dumps(value,indent=2))
        temporary.replace(Path(root)/"status.json")
    except PermissionError:
        logging.getLogger(__name__).debug("status snapshot locked; retry on next publication")
        return False
    return True

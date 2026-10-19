"""Configuración común de pytest: raíz del proyecto en sys.path y datos aislados."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

# Los tests nunca deben tocar el data/ real: se redirige antes de importar config.
os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="plantvillage_tests_"))

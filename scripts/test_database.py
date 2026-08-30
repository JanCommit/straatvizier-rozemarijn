"""Voer een minimale handmatige controle van de StraatVizier-databaselaag uit.

Dit is geen pytest-test; het roept ``get_streets`` rechtstreeks aan en print het resultaat."""

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(
    0,
    str(PROJECT_ROOT / "src"),
)


from straatvizier.database import get_streets


streets = get_streets()

print(streets)
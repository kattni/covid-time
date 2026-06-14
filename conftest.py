import sys
from pathlib import Path

# Make the src/ layout importable under pytest without an editable install.
sys.path.insert(0, str(Path(__file__).parent / "src"))

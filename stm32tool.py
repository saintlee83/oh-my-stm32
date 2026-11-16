"""Repository entry point; the same CLI ships inside the standalone skill."""
from pathlib import Path
import runpy
import sys

scripts = Path(__file__).resolve().parent / ".agents/skills/stm32-workbench/scripts"
sys.path.insert(0, str(scripts))
runpy.run_path(str(scripts / "stm32_toolkit.py"), run_name="__main__")

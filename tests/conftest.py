import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADDON = os.path.join(ROOT, 'src', 'script.papa.inicio')
if ADDON not in sys.path:
    sys.path.insert(0, ADDON)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

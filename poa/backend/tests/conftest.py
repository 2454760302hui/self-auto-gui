import sys
import os

# Add parent of backend/ so 'backend' is importable as a package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Set POA_SECRET for tests (auth.py requires it)
os.environ.setdefault("POA_SECRET", "test-secret-key-for-pytest-only")

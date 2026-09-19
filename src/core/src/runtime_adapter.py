import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import os
from .runtime_bridge import O22Bridge


class RuntimeAdapter:
    """
    Small evaluation-only adapter around the O22/O23-style integrated runtime.
    It keeps the harness independent from the operator/control-plane internals.
    """

    def __init__(self, root):
        self.root=root
        self.bridge=O22Bridge(root)

    def run(self, run_id, project_id, request):
        return self.bridge.run(run_id,project_id,request)


    def close(self):
        if getattr(self, "_closed", False):
            return
        self._closed = True
        self.bridge.close()

    def __enter__(self):
        if getattr(self, "_closed", False):
            raise RuntimeError("RuntimeAdapter is closed")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False

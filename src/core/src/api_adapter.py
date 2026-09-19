from .api import InProcessAPI


class O32APIAdapter(InProcessAPI):
    """
    Explicit transport adapter.
    Keeps the existing O26 service contract unchanged.
    """
    pass

"""Official Python client for the VisionTrader market data API."""

from visiontrader.exceptions import ApiError, SnapshotError, ValidationError, VisionTraderError
from visiontrader.models import Expiry, OptionLeg, OptionsSnapshot
from visiontrader.options import OptionsClient

__version__ = "0.1.0"

__all__ = [
    "ApiError",
    "Expiry",
    "OptionLeg",
    "OptionsClient",
    "OptionsSnapshot",
    "SnapshotError",
    "ValidationError",
    "VisionTraderError",
    "__version__",
    "options_client",
]


def options_client(**kwargs) -> OptionsClient:
    """Create an :class:`OptionsClient` (for ``import visiontrader as vt``)."""
    return OptionsClient(**kwargs)

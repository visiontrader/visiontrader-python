"""Official Python client for the VisionTrader market data API."""

from visiontrader.auth import setup_key
from visiontrader.exceptions import ApiError, SnapshotError, ValidationError, VisionTraderError
from visiontrader.models import Expiry, OptionLeg, OptionsSnapshot, SnapshotInfo
from visiontrader.smile_analytics import ImpliedForwardModel
from visiontrader.options import VisionOptionsClient

__version__ = '0.1.0'

__all__ = [
    'ApiError',
    'Expiry',
    'ImpliedForwardModel',
    'OptionLeg',
    'OptionsSnapshot',
    'SnapshotInfo',
    'SnapshotError',
    'ValidationError',
    'VisionOptionsClient',
    'VisionTraderError',
    '__version__',
    'setup_key',
    'vision_options_client',
]


def vision_options_client(**kwargs) -> VisionOptionsClient:
    """Create a :class:`VisionOptionsClient` (for ``import visiontrader as vt``)."""
    return VisionOptionsClient(**kwargs)

"""QCF -- Quant Currency Futures.

Research and paper-simulation tooling for CME Euro FX futures (``6E``).

QCF has no live operating mode and no capability to transmit, modify, or cancel
a real order. Permitted modes are ``DISABLED``, ``RESEARCH``, ``BACKTEST``,
``REPLAY``, and ``PAPER``; the default is ``DISABLED``.
"""

from qcf.core.version import __version__

__all__ = ["__version__"]

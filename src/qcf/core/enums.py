"""Core enumerations shared across QCF.

Stage 00 defines enumeration *values* only. The behaviour those values will
eventually govern -- the paper halt state machine, risk actions, compliance
actions, data-quality routing -- belongs to later stages and is deliberately
absent here. Declaring the vocabulary early keeps later stages from inventing
competing spellings of the same concept; implementing the behaviour early would
be later-stage work smuggled into the foundation.
"""

from __future__ import annotations

from enum import StrEnum

__all__ = [
    "DataQualityDisposition",
    "HaltState",
    "OperatingMode",
    "Severity",
]


class OperatingMode(StrEnum):
    """The modes QCF is permitted to operate in.

    There is deliberately no ``LIVE`` member, and there never may be one. QCF is
    a research and paper-simulation system that must not be able to transmit a
    real order, and the absence of a live mode is one of the mechanisms that
    makes that true rather than merely intended.

    The default everywhere is :attr:`DISABLED`: a QCF process that has not been
    told what it is for does nothing.
    """

    DISABLED = "DISABLED"
    RESEARCH = "RESEARCH"
    BACKTEST = "BACKTEST"
    REPLAY = "REPLAY"
    PAPER = "PAPER"


class HaltState(StrEnum):
    """States of the latched paper-operation halt machine.

    Declared in Stage 00 so that incident, monitoring, and reporting code share
    one vocabulary. The state machine itself -- its transitions, its latching,
    and its refusal to resume automatically -- is Stage 16 work and is not
    implemented here.
    """

    DISABLED = "DISABLED"
    READY = "READY"
    RUNNING_PAPER = "RUNNING_PAPER"
    ENTRY_BLOCKED = "ENTRY_BLOCKED"
    FLATTENING_SIMULATED = "FLATTENING_SIMULATED"
    HALTED = "HALTED"
    INVESTIGATION_REQUIRED = "INVESTIGATION_REQUIRED"
    REVALIDATION_REQUIRED = "REVALIDATION_REQUIRED"


class Severity(StrEnum):
    """Severity of a finding, alert, or incident."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DataQualityDisposition(StrEnum):
    """The permitted outcomes of a data-quality finding.

    Every finding must receive exactly one of these. ``FLAG`` records a concern
    without blocking; ``QUARANTINE`` removes rows from research use while
    preserving them; ``REJECT_DATASET`` refuses the dataset as a whole; and
    ``REQUIRES_HUMAN_DECISION`` exists so that an ambiguity is escalated instead
    of being resolved by a default. Silently dropping suspicious data is not an
    available outcome.
    """

    ACCEPT = "ACCEPT"
    FLAG = "FLAG"
    QUARANTINE = "QUARANTINE"
    REJECT_DATASET = "REJECT_DATASET"
    REQUIRES_HUMAN_DECISION = "REQUIRES_HUMAN_DECISION"

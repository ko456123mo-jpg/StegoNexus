"""
StegoNexus - Unified Hiding, Extraction & Forensics Framework
=============================================================
Project Summary: StegoNexus converts the Hiding & Extraction techniques
covered during the term into one integrated tool running on Kali Linux.
It provides a unified Dashboard that allows the user to choose the desired
hiding type, or move to the Forensics / Analysis section to inspect files
and search for indicators of hidden data.

Prepared & Developed by: Mohammed Moneer Al-absi
"""

__version__ = "1.0.0"
__author__ = "Mohammed Moneer Al-absi"

from stegonexus.core import (
    hashing,
    entropy,
    text_hiding,
    image_stego,
    image_steghide,
    audio_hiding,
    video_hiding,
    network_hiding,
    malware_lab,
    forensics,
)
from stegonexus.case.manager import CaseManager

__all__ = [
    "__version__",
    "__author__",
    "hashing",
    "entropy",
    "text_hiding",
    "image_stego",
    "image_steghide",
    "audio_hiding",
    "video_hiding",
    "network_hiding",
    "malware_lab",
    "forensics",
    "CaseManager",
]

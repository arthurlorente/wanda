"""Verified HTTPS contexts using platform trust, with a narrow macOS fallback."""

from pathlib import Path
import ssl
import sys


def create_https_context():
    """Keep Python's default trust and verification; repair empty macOS stores.

    Some portable Python builds cannot locate their compiled-in CA paths on macOS.
    Only when no CAs are loaded do we try the fixed, OS-managed certificate bundle.
    An absent or unreadable bundle leaves the verified default context in place;
    a connection without usable trust still fails certificate verification.
    """
    context = ssl.create_default_context()
    if sys.platform == "darwin" and not context.get_ca_certs():
        system_bundle = Path("/etc/ssl/cert.pem")
        try:
            if system_bundle.is_file():
                context.load_verify_locations(cafile=str(system_bundle))
        except (OSError, ssl.SSLError):
            # Never recover by disabling certificate or hostname verification.
            pass
    return context

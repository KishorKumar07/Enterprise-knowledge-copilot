"""A merged CA bundle (certifi + the Windows Root store), generated once and
cached in the OS temp dir.

Some networks (this dev machine included — likely antivirus or a corporate
proxy doing TLS inspection) present a certificate chain that only the OS
trust store recognizes, not the certifi bundle Python ships with. The usual
fix is `truststore`, which patches `ssl.SSLContext` to consult the OS store
at connect time — but its asyncio integration has a recursion bug on Windows
(reproduced against both the Gemini and Groq async clients here). Baking the
OS roots into a static PEM file once and pointing httpx at it sidesteps that
entirely: it's plain, unpatched `ssl.SSLContext`, just with a bigger CA list.

This is a workaround for one specific class of dev machine, not something a
normally-configured host (e.g. a cloud deployment) should ever need — so
`install()` never lets a failure here crash the app. Worst case, everything
just falls back to the certifi bundle Python already ships with.
"""

import logging
import os
import ssl
import sys
import tempfile
from pathlib import Path

import certifi

logger = logging.getLogger("ekc.ssl_bundle")

_BUNDLE_PATH = Path(tempfile.gettempdir()) / "ekc-ca-bundle.pem"


def _build_bundle() -> Path:
    certs_pem = [Path(certifi.where()).read_text(encoding="utf-8")]

    if sys.platform == "win32":
        for der_bytes, _encoding, trusted in ssl.enum_certificates("ROOT"):
            if trusted:
                certs_pem.append(ssl.DER_cert_to_PEM_cert(der_bytes))

    _BUNDLE_PATH.write_text("\n".join(certs_pem), encoding="utf-8")
    return _BUNDLE_PATH


def get_ca_bundle_path() -> str:
    if not _BUNDLE_PATH.exists():
        _build_bundle()
    return str(_BUNDLE_PATH)


def install() -> None:
    """Point standard cert env vars (requests, huggingface_hub, urllib3, the
    stdlib ssl module) at the merged bundle. Call once, early at process
    startup, before anything that might make an HTTPS request."""
    try:
        path = get_ca_bundle_path()
    except OSError:
        logger.warning("Could not build merged CA bundle — falling back to the default certifi bundle.", exc_info=True)
        return

    os.environ.setdefault("SSL_CERT_FILE", path)
    os.environ.setdefault("REQUESTS_CA_BUNDLE", path)
    os.environ.setdefault("CURL_CA_BUNDLE", path)

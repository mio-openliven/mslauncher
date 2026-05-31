from __future__ import annotations

import ipaddress
from urllib.parse import urlparse


class URLPolicyError(ValueError):
    pass


def normalize_https_url(
    raw_url: object,
    field_name: str,
    *,
    allow_insecure_local: bool = False,
) -> str:
    if not isinstance(raw_url, str):
        raise URLPolicyError(f"{field_name} must be a URL string.")

    url = raw_url.strip()
    parsed_url = urlparse(url)

    if not parsed_url.scheme:
        raise URLPolicyError(f"{field_name} must include https://.")
    if parsed_url.scheme not in ("https", "http"):
        raise URLPolicyError(f"{field_name} must use https://.")
    if parsed_url.scheme == "http" and not allow_insecure_local:
        raise URLPolicyError(f"{field_name} must use https://. HTTP is not supported.")
    if parsed_url.scheme == "http" and not is_local_host(parsed_url.hostname or ""):
        raise URLPolicyError(f"{field_name} may use HTTP only for explicit local tests.")
    if not parsed_url.hostname:
        raise URLPolicyError(f"{field_name} must include a host.")
    if parsed_url.username or parsed_url.password:
        raise URLPolicyError(f"{field_name} must not contain username or password.")
    if parsed_url.fragment:
        raise URLPolicyError(f"{field_name} must not contain a URL fragment.")
    if not allow_insecure_local and is_local_host(parsed_url.hostname):
        raise URLPolicyError(f"{field_name} must not point to localhost or a private IP in production.")

    return url


def normalize_source_key_url(source_key: object, *, allow_insecure_local: bool = False) -> str:
    if not isinstance(source_key, str):
        raise URLPolicyError("source_key must be a string.")

    stripped_source = source_key.strip()
    if not stripped_source:
        raise URLPolicyError("source_key must not be empty.")

    if "://" in stripped_source:
        # Full raw.githubusercontent.com source_key values are treated as ordinary public HTTPS URLs.
        # A launcher password gate can block UI downloads, but it cannot make public raw files secret.
        return normalize_https_url(stripped_source, "source_key", allow_insecure_local=allow_insecure_local)

    host_candidate = stripped_source.strip("/")
    if not host_candidate:
        raise URLPolicyError("source_key host must not be empty.")
    if "@" in host_candidate:
        raise URLPolicyError("source_key must not contain username or password.")
    if "#" in host_candidate:
        raise URLPolicyError("source_key must not contain a URL fragment.")

    return normalize_https_url(
        f"https://{host_candidate}/mslauncher/build.json",
        "source_key",
        allow_insecure_local=allow_insecure_local,
    )


def ensure_same_https_origin(source_url: str, target_url: str, *, field_name: str) -> str:
    source = urlparse(source_url)
    target = urlparse(target_url)
    if target.scheme != "https":
        raise URLPolicyError(f"{field_name} redirect must stay on https://.")
    if target.username or target.password:
        raise URLPolicyError(f"{field_name} redirect must not contain username or password.")
    if target.fragment:
        raise URLPolicyError(f"{field_name} redirect must not contain a URL fragment.")
    if source.hostname != target.hostname or source.port != target.port:
        raise URLPolicyError(f"{field_name} redirect changed host, which is not allowed.")
    return target_url


def is_local_host(hostname: str) -> bool:
    normalized_host = hostname.strip().lower()
    if normalized_host in ("localhost",):
        return True

    try:
        ip_address = ipaddress.ip_address(normalized_host)
    except ValueError:
        return False

    return (
        ip_address.is_private
        or ip_address.is_loopback
        or ip_address.is_link_local
        or ip_address.is_reserved
        or ip_address.is_multicast
    )

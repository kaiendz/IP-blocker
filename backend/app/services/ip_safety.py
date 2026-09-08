"""Safety net: IPs/CIDRs that must never be auto-blacklisted, no matter the source."""
import ipaddress
from typing import Iterable

# Private, loopback, link-local, and reserved ranges. Never auto-blacklist anything
# inside these even if a threat-intel feed or a buggy rule tries to.
_ALWAYS_SAFE_NETS = [
    ipaddress.ip_network(n)
    for n in [
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "127.0.0.0/8",
        "169.254.0.0/16",
        "::1/128",
        "fc00::/7",
        "fe80::/10",
    ]
]


def is_valid_ip_or_cidr(value: str) -> bool:
    try:
        if "/" in value:
            ipaddress.ip_network(value, strict=False)
        else:
            ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def is_always_safe(value: str) -> bool:
    """True if this IP/CIDR falls inside a hardcoded private/reserved range."""
    try:
        net = ipaddress.ip_network(value, strict=False) if "/" in value else ipaddress.ip_network(
            f"{value}/32" if ipaddress.ip_address(value).version == 4 else f"{value}/128"
        )
    except ValueError:
        return False
    return any(net.overlaps(safe) for safe in _ALWAYS_SAFE_NETS)


def is_allowlisted(value: str, allowlist_nets: Iterable[str]) -> bool:
    try:
        net = ipaddress.ip_network(value, strict=False)
    except ValueError:
        return False
    for entry in allowlist_nets:
        try:
            allow_net = ipaddress.ip_network(entry, strict=False)
        except ValueError:
            continue
        if net.overlaps(allow_net):
            return True
    return False

from datetime import datetime, timedelta, timezone

from app.services.detection import find_offenders

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _events(ip: str, count: int, minutes_ago_start: int = 1) -> list[tuple[str, datetime]]:
    return [(ip, NOW - timedelta(minutes=minutes_ago_start + i)) for i in range(count)]


def test_ip_at_threshold_is_flagged():
    events = _events("1.2.3.4", 5)
    offenders = find_offenders(events, threshold_count=5, window_minutes=10, now=NOW)
    assert offenders == {"1.2.3.4": 5}


def test_ip_below_threshold_is_not_flagged():
    events = _events("1.2.3.4", 4)
    offenders = find_offenders(events, threshold_count=5, window_minutes=10, now=NOW)
    assert offenders == {}


def test_events_outside_window_are_excluded():
    events = _events("1.2.3.4", 3) + _events("1.2.3.4", 3, minutes_ago_start=20)
    offenders = find_offenders(events, threshold_count=5, window_minutes=10, now=NOW)
    assert offenders == {}  # only 3 fall inside the 10-minute window


def test_multiple_ips_evaluated_independently():
    events = _events("1.1.1.1", 6) + _events("2.2.2.2", 2)
    offenders = find_offenders(events, threshold_count=5, window_minutes=10, now=NOW)
    assert offenders == {"1.1.1.1": 6}


def test_exactly_at_window_boundary_is_included():
    events = [("1.2.3.4", NOW - timedelta(minutes=10))] * 5
    offenders = find_offenders(events, threshold_count=5, window_minutes=10, now=NOW)
    assert offenders == {"1.2.3.4": 5}


def test_no_events_returns_empty():
    assert find_offenders([], threshold_count=5, window_minutes=10, now=NOW) == {}

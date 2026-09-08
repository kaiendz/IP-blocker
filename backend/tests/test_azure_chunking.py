from app.services.azure_publisher import build_chunks, compute_hash


def test_chunks_respect_max_size():
    ips = [f"10.0.0.{i}" for i in range(250)]
    chunks = build_chunks(ips, chunk_size=100)
    assert len(chunks) == 3
    assert [len(c) for c in chunks] == [100, 100, 50]


def test_chunks_are_deduplicated_and_sorted():
    ips = ["3.3.3.3", "1.1.1.1", "2.2.2.2", "1.1.1.1"]
    chunks = build_chunks(ips, chunk_size=10)
    assert chunks == [["1.1.1.1", "2.2.2.2", "3.3.3.3"]]


def test_empty_list_produces_no_chunks():
    assert build_chunks([], chunk_size=100) == []


def test_shrinking_list_produces_fewer_chunks():
    big = build_chunks([f"10.0.0.{i}" for i in range(150)], chunk_size=100)
    small = build_chunks([f"10.0.0.{i}" for i in range(20)], chunk_size=100)
    assert len(big) == 2
    assert len(small) == 1


def test_hash_changes_with_content():
    h1 = compute_hash(["1.1.1.1", "2.2.2.2"])
    h2 = compute_hash(["1.1.1.1", "2.2.2.3"])
    h3 = compute_hash(["1.1.1.1", "2.2.2.2"])
    assert h1 != h2
    assert h1 == h3


def test_invalid_chunk_size_rejected():
    import pytest

    with pytest.raises(ValueError):
        build_chunks(["1.1.1.1"], chunk_size=0)

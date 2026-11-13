import pytest
from helpers import capture_at_k


def test_capture_perfect_ranking_at_base_rate():
    y = [1, 1, 0, 0, 0, 0, 0, 0, 0, 0]
    score = [0.9, 0.8, 0.5, 0.4, 0.3, 0.2, 0.1, 0.05, 0.02, 0.01]
    assert capture_at_k(y, score, 0.2) == 1.0


def test_capture_worst_ranking():
    y = [0, 0, 0, 0, 0, 0, 0, 0, 1, 1]
    score = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.05]
    assert capture_at_k(y, score, 0.2) == 0.0


def test_capture_k_one_is_one():
    assert capture_at_k([0, 1, 0, 1, 0], [0.3, 0.1, 0.9, 0.2, 0.5], 1) == 1.0


def test_capture_mixed_example():
    # ranking by score: idx 2 (0), idx 0 (1), idx 4 (0), idx 1 (1), idx 3 (0)
    y = [1, 1, 0, 0, 0]
    score = [0.8, 0.4, 0.9, 0.1, 0.5]
    # top ceil(0.4 * 5) = 2 -> idx 2, 0 -> one of two positives
    assert capture_at_k(y, score, 0.4) == 0.5
    # top ceil(0.8 * 5) = 4 -> idx 2, 0, 4, 1 -> both positives
    assert capture_at_k(y, score, 0.8) == 1.0


def test_capture_ties_broken_by_original_order():
    y = [0, 1, 0, 1]
    score = [1.0, 1.0, 1.0, 1.0]
    assert capture_at_k(y, score, 0.5) == 0.5  # top two are idx 0, 1
    y2 = [1, 0, 0, 1]
    assert capture_at_k(y2, score, 0.25) == 0.5  # top one is idx 0


def test_capture_length_mismatch():
    with pytest.raises(ValueError):
        capture_at_k([1, 0, 0], [0.1, 0.2], 0.5)


@pytest.mark.parametrize("k", [0, -0.1, 1.5])
def test_capture_bad_k(k):
    with pytest.raises(ValueError):
        capture_at_k([1, 0, 0], [0.3, 0.2, 0.1], k)


def test_capture_no_positives():
    with pytest.raises(ValueError):
        capture_at_k([0, 0, 0], [0.3, 0.2, 0.1], 0.5)

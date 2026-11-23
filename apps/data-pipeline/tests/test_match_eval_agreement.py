"""Kappa trong so cho nhan danh gia 017 (pipeline/match_eval_agreement.py)."""
import json
from pathlib import Path

import pytest

from pipeline.match_eval_agreement import agreement, weighted_kappa

SEEDS = Path(__file__).resolve().parents[1] / "data" / "seeds" / "match_eval"


def test_perfect_agreement_is_one():
    assert weighted_kappa([0, 1, 2, 2], [0, 1, 2, 2]) == pytest.approx(1.0)


def test_hand_computed_example():
    # obs = [[1,1,0],[0,1,0],[0,0,1]], n=4; observed = w01 * 1 = 0.25
    # rows [2,1,1], cols [1,2,1]; expected = sum w_ij * r_i * c_j / n
    # = (0.25*2*2 + 1*2*1 + 0.25*1*1 + 0.25*1*1 + 1*1*1 + 0.25*1*2) / 4 = (1 + 2 + 0.25 + 0.25 + 1 + 0.5) / 4 = 1.25
    assert weighted_kappa([0, 0, 1, 2], [0, 1, 1, 2]) == pytest.approx(1 - 0.25 / 1.25)


def test_missing_reference_pair_is_an_error():
    with pytest.raises(ValueError):
        agreement({"cv": {"jd1": 1}}, {"cv": {}})


def test_committed_blind_labels_reproduce_reported_kappa():
    de = json.loads((SEEDS / "de_blind_labels.json").read_text(encoding="utf-8"))["labels"]
    final = json.loads((SEEDS / "labels.json").read_text(encoding="utf-8"))
    result = agreement(de, final["labels"])
    assert result["n"] == 48
    assert result["weighted_kappa"] == final["agreement"]["weighted_kappa_quadratic"]

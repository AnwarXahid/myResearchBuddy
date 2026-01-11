import pytest

from app.workflow import Part2Output


def test_part2_requires_four_rqs():
    with pytest.raises(ValueError):
        Part2Output(
            titles=["t"],
            rqs=[
                {
                    "question": "Q1",
                    "hypothesis": "H",
                    "metrics": ["m"],
                    "minimal_experiment": "exp",
                    "baselines": ["b"],
                    "ablations": ["a"],
                }
            ],
            experiment_matrix={},
        )

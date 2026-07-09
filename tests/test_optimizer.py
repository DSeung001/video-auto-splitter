from __future__ import annotations

import numpy as np
import pytest

from lecture_splitter.config import load_config
from lecture_splitter.optimizer import _otsu_threshold, optimize_audio_config_from_db_values


def _make_config():
    return load_config(None).audio


def test_otsu_threshold_separates_two_clear_clusters() -> None:
    rng = np.random.default_rng(42)
    quiet = rng.normal(loc=-45.0, scale=1.5, size=200)
    active = rng.normal(loc=-20.0, scale=1.5, size=400)
    values = np.concatenate([quiet, active])

    threshold = _otsu_threshold(values)

    assert -45.0 < threshold < -20.0


def test_optimize_audio_config_from_db_values_detects_break_and_active_levels() -> None:
    config = _make_config()
    rng = np.random.default_rng(7)
    # Simulate a break with mild background noise (not dead silence) and an
    # active lecture segment with louder speech.
    quiet = rng.normal(loc=-42.0, scale=2.0, size=300)
    active = rng.normal(loc=-18.0, scale=2.0, size=700)
    db_values = np.concatenate([quiet, active])

    result = optimize_audio_config_from_db_values(db_values, config)

    assert result.quiet_mean_db < result.active_mean_db
    assert result.quiet_mean_db == pytest.approx(-42.0, abs=3.0)
    assert result.active_mean_db == pytest.approx(-18.0, abs=3.0)
    assert result.sample_count == db_values.size
    assert 0.0 < result.quiet_ratio < 1.0

    # The optimized absolute cutoff should sit above the quiet cluster's own
    # noise floor (accounting for break-time background noise) but below the
    # active cluster's level.
    assert result.quiet_mean_db < result.config.absolute_quiet_db < result.active_mean_db
    assert result.config.relative_drop_db > 0
    assert result.config.absolute_margin_db > 0
    assert 0.55 <= result.config.quiet_score_threshold <= 0.70


def test_optimize_audio_config_from_db_values_handles_degenerate_input() -> None:
    config = _make_config()
    # Almost no variation at all (e.g. a very short clip / constant tone).
    db_values = np.full(10, -30.0)

    result = optimize_audio_config_from_db_values(db_values, config)

    assert result.sample_count == 10
    assert result.config.absolute_margin_db >= 3.0
    assert result.config.relative_drop_db >= 4.0


def test_optimize_audio_config_from_db_values_rejects_empty_array() -> None:
    config = _make_config()
    with pytest.raises(RuntimeError):
        optimize_audio_config_from_db_values(np.array([]), config)

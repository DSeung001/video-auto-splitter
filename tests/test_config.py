from __future__ import annotations

from pathlib import Path

import pytest

from lecture_splitter.config import load_config, write_config_template


def test_load_config_without_path_uses_defaults() -> None:
    config = load_config(None)
    assert config.audio.sample_rate == 16000
    assert config.scoring.audio_weight == pytest.approx(0.7)
    assert config.split.default_copy_mode is True
    assert config.split.verify_decode_with_ffmpeg is False


def test_write_config_template_with_preset(tmp_path: Path) -> None:
    config_path = tmp_path / "strict.yaml"
    write_config_template(str(config_path), preset="strict", overwrite=False)

    loaded = load_config(str(config_path))
    assert loaded.audio.absolute_quiet_db == pytest.approx(-42.0)
    assert loaded.break_detection.min_break_duration_sec == pytest.approx(240.0)


def test_write_config_template_respects_overwrite_flag(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    write_config_template(str(config_path), overwrite=False)
    with pytest.raises(FileExistsError):
        write_config_template(str(config_path), overwrite=False)

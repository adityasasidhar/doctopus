"""Sidecar engines are only 'ready' once their weights are on disk, not merely when the CLI is installed."""
from doctopus.backends import sidecar


def test_marker_needs_layout_weights(monkeypatch, tmp_path):
    monkeypatch.setattr(sidecar.shutil, "which", lambda exe: f"/opt/{exe}")
    monkeypatch.setenv("HF_HUB_CACHE", str(tmp_path))
    info = sidecar.MarkerBackend().info()
    assert not info.available and "surya_layout2" in info.reason_unavailable

    snap = tmp_path / "models--datalab-to--surya_layout2/snapshots/abc"
    snap.mkdir(parents=True)
    (snap / "rfdetr_layout.pth").write_bytes(b"w")
    assert sidecar.MarkerBackend().info().available


def test_mineru_needs_basic_tier_weights(monkeypatch, tmp_path):
    monkeypatch.setattr(sidecar.shutil, "which", lambda exe: f"/opt/{exe}")
    monkeypatch.setenv("DOCTOPUS_MINERU_MODELS", str(tmp_path))
    root = tmp_path / "MinerU-4_models_onnx"
    for m in sidecar.MinerUBackend._MODELS[:-1]:
        (root / m).parent.mkdir(parents=True, exist_ok=True)
        (root / m).write_bytes(b"w")
    info = sidecar.MinerUBackend().info()
    assert not info.available and "mineru-kit models download" in info.reason_unavailable

    last = root / sidecar.MinerUBackend._MODELS[-1]
    last.parent.mkdir(parents=True, exist_ok=True)
    last.write_bytes(b"w")
    assert sidecar.MinerUBackend().info().available


def test_missing_cli_reports_install_hint(monkeypatch):
    monkeypatch.setattr(sidecar.shutil, "which", lambda exe: None)
    assert sidecar.MarkerBackend().info().reason_unavailable == sidecar.MarkerBackend.install

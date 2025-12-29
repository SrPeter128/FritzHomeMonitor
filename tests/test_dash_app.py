from datetime import timedelta

import pandas as pd

import dash_app


def test_list_device_files_excludes_devices_tsv(tmp_path, monkeypatch):
    (tmp_path / "devices.tsv").write_text("Timestamp\tNewDeviceName\n", encoding="utf-8")
    (tmp_path / "plug.tsv").write_text("Timestamp\tNewDeviceName\n", encoding="utf-8")
    (tmp_path / "sensor.tsv").write_text("Timestamp\tNewDeviceName\n", encoding="utf-8")

    monkeypatch.setattr(dash_app, "DATA_DIR", tmp_path)

    files = dash_app.list_device_files()
    assert [p.name for p in files] == ["plug.tsv", "sensor.tsv"]


def test_load_device_df_parses_and_sorts(tmp_path):
    data = "\n".join(
        [
            "Timestamp\tNewMultimeterPower",
            "2024-01-02T12:00:00\t10",
            "2024-01-01T12:00:00\t20",
        ]
    )
    path = tmp_path / "plug.tsv"
    path.write_text(data, encoding="utf-8")

    df = dash_app.load_device_df(path)

    assert len(df) == 2
    assert df.iloc[0]["NewMultimeterPower"] == 20
    assert df.iloc[1]["NewMultimeterPower"] == 10


def test_filter_df_by_range_filters_hour():
    now = pd.Timestamp.now()
    df = pd.DataFrame(
        {
            "Timestamp": [now - timedelta(hours=2), now - timedelta(minutes=30)],
            "NewMultimeterPower": [1, 2],
        }
    )

    filtered = dash_app.filter_df_by_range(df, "hour")

    assert len(filtered) == 1
    assert filtered.iloc[0]["NewMultimeterPower"] == 2


def test_build_time_axis_falls_back_to_index():
    df = pd.DataFrame({"NewMultimeterPower": [1, 2, 3]})

    axis = dash_app.build_time_axis(df)

    assert axis == [0, 1, 2]


def test_clamp_log_series_clips_values():
    df = pd.DataFrame({"NewMultimeterPower": [0.01, 0.2]})

    clamped = dash_app.clamp_log_series(df, "NewMultimeterPower", 0.1)

    assert clamped["NewMultimeterPower"].tolist() == [0.1, 0.2]

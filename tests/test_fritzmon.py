import importlib
import sys
import types


def _load_fritzmon():
    fritzconnection = types.ModuleType("fritzconnection")

    class DummyConnection:
        pass

    fritzconnection.FritzConnection = DummyConnection

    fritzconnection_lib = types.ModuleType("fritzconnection.lib")
    fritzhomeauto = types.ModuleType("fritzconnection.lib.fritzhomeauto")

    class DummyHomeAutomation:
        pass

    fritzhomeauto.FritzHomeAutomation = DummyHomeAutomation

    sys.modules["fritzconnection"] = fritzconnection
    sys.modules["fritzconnection.lib"] = fritzconnection_lib
    sys.modules["fritzconnection.lib.fritzhomeauto"] = fritzhomeauto

    return importlib.import_module("fritzmon")


fritzmon = _load_fritzmon()


def test_sanitize_filename():
    assert fritzmon._sanitize_filename("Living Room") == "Living_Room"
    assert fritzmon._sanitize_filename("plug-01") == "plug-01"
    assert fritzmon._sanitize_filename("**") == "device"


def test_write_device_tsv_per_device(tmp_path):
    devices = [
        {
            "NewDeviceName": "Plug 1",
            "NewMultimeterPower": 200000,
            "NewMultimeterEnergy": 4500,
            "NewTemperatureCelsius": 235,
            "NewSwitchState": "ON",
        }
    ]
    fritzmon.write_device_tsv_per_device(devices, output_dir=tmp_path)

    tsv_path = tmp_path / "Plug_1.tsv"
    assert tsv_path.exists()

    lines = tsv_path.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("Timestamp\tNewDeviceName\tNewMultimeterPower")

    row = lines[1].split("\t")
    assert row[1] == "Plug 1"
    assert row[2] == "2.0"
    assert row[3] == "4.5"
    assert row[4] == "23.5"
    assert row[5] == "ON"

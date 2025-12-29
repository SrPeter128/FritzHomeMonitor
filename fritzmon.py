from multiprocessing.util import info
from fritzconnection import FritzConnection
from fritzconnection.lib.fritzhomeauto import FritzHomeAutomation
from datetime import datetime
import os
import time

def _sanitize_filename(value):
    safe = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in value)
    return safe or "device"


def write_device_tsv_per_device(devices, output_dir="."):
    headers = [
        "Timestamp",
        "NewDeviceName",
        "NewMultimeterPower",
        "NewMultimeterEnergy",
        "NewTemperatureCelsius",
        "NewSwitchState",
    ]
    for device in devices:
        device_name = str(device.get("NewDeviceName", "device"))
        filename = _sanitize_filename(device_name) + ".tsv"
        tsv_path = f"{output_dir}/{filename}".replace("//", "/")
        file_exists = os.path.exists(tsv_path)
        with open(tsv_path, "a", encoding="utf-8") as f:
            timestamp = datetime.now().isoformat(timespec="seconds")
            if not file_exists:
                f.write("\t".join(headers) + "\n")
            for key in headers[1:]:
                if key not in device:
                    device[key] = ""
                elif key == "NewTemperatureCelsius":
                    temp = float(device[key] * 0.1)
                elif key == "NewMultimeterPower":
                    power = float(device[key] * 0.00001)
                elif key == "NewMultimeterEnergy":
                    energy = float(device[key]) * 0.001
            row = [timestamp]+ [device.get("NewDeviceName")] + [ str(power), str(energy), str(temp)] + [str(device.get(key, "")) for key in headers[5:]]
            f.write("\t".join(row) + "\n")


if __name__ == "__main__":
   
    print("Starte Fritzmon...")
    with open("login.crd", "r") as login:
        login_data = login.read().split()
    
    fh = FritzHomeAutomation()
    fha = FritzHomeAutomation(address='192.168.178.1', user=login_data[0], password=login_data[1])
    
    print("Login erfolgreich...")

    while True:
        info = fha.device_information()
        write_device_tsv_per_device(info)
        time.sleep(45)  # Wait for 45 seconds before the next poll
        print("Wrote device data at", datetime.now().isoformat(timespec="seconds"))

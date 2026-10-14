from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
from datetime import time

from .database import AttendanceRepository


@dataclass
class ScanResult:
    address: str
    name: str | None
    rssi: int | None
    registered_student: str | None


async def scan_nearby(
    repository: AttendanceRepository,
    timeout: float = 8.0,
    late_after: time | None = None,
) -> list[ScanResult]:
    """Discover BLE devices once and persist detections for known beacon addresses."""
    try:
        from bleak import BleakScanner
    except ImportError as exc:
        raise RuntimeError("BLE support is not installed. Run: pip install -r requirements.txt") from exc

    devices = await BleakScanner.discover(timeout=timeout, return_adv=True)
    results: list[ScanResult] = []
    # bleak returns {address: (BLEDevice, AdvertisementData)} with return_adv=True.
    for device, advertisement in devices.values():
        name = device.name or advertisement.local_name
        rssi = getattr(advertisement, "rssi", None)
        student = repository.record_detection(device.address, name=name, rssi=rssi, late_after=late_after)
        results.append(
            ScanResult(
                address=device.address,
                name=name,
                rssi=rssi,
                registered_student=student["name"] if student else None,
            )
        )
    return results


def scan_once(
    repository: AttendanceRepository,
    timeout: float = 8.0,
    late_after: time | None = None,
) -> list[dict]:
    """Synchronous wrapper suitable for Streamlit and the command line."""
    return [asdict(result) for result in asyncio.run(scan_nearby(repository, timeout, late_after))]

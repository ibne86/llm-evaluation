"""Optional Windows whole-system physical-memory snapshots."""

import ctypes
import sys
from ctypes import wintypes


class MemoryStatus(ctypes.Structure):
    _fields_ = [
        ("length", wintypes.DWORD), ("load_percent", wintypes.DWORD),
        ("total_physical", ctypes.c_ulonglong), ("available_physical", ctypes.c_ulonglong),
        ("total_page_file", ctypes.c_ulonglong), ("available_page_file", ctypes.c_ulonglong),
        ("total_virtual", ctypes.c_ulonglong), ("available_virtual", ctypes.c_ulonglong),
        ("available_extended_virtual", ctypes.c_ulonglong),
    ]


def memory_snapshot():
    if sys.platform != "win32":
        return {"available_gib": None, "note": "Windows physical-memory measurement unavailable."}
    status = MemoryStatus()
    status.length = ctypes.sizeof(status)
    get_status = ctypes.WinDLL("kernel32", use_last_error=True).GlobalMemoryStatusEx
    get_status.argtypes = [ctypes.POINTER(MemoryStatus)]
    get_status.restype = wintypes.BOOL
    if not get_status(ctypes.byref(status)):
        raise ctypes.WinError(ctypes.get_last_error())
    return {
        "available_bytes": status.available_physical,
        "available_gib": round(status.available_physical / 1024**3, 3),
        "system_memory_load_percent": status.load_percent,
    }

#!/usr/bin/env python3
"""Show information about this computer using only Python's standard library."""
import os
import platform
import shutil


def meminfo():
    info = {}
    with open("/proc/meminfo") as fh:
        for line in fh:
            key, value = line.split(":", 1)
            info[key] = int(value.split()[0]) // 1024  # MB
    return info


mem = meminfo()
disk = shutil.disk_usage("/")
with open("/etc/os-release") as fh:
    osr = dict(line.strip().split("=", 1) for line in fh if "=" in line)

print(f"System   : {osr.get('PRETTY_NAME', '').strip(chr(34))}")
print(f"Kernel   : {platform.release()}")
print(f"Python   : {platform.python_version()}")
print(f"CPUs     : {os.cpu_count()}")
print(f"RAM      : {mem['MemTotal'] - mem['MemAvailable']} MB used of {mem['MemTotal']} MB")
print(f"Disk (/) : {disk.used // 2**30} GB used of {disk.total // 2**30} GB")
try:
    with open("/run/claudius/tune") as fh:
        profile = dict(l.strip().split("=", 1) for l in fh if "=" in l)
    print(f"Profile  : {profile.get('PROFILE')} (chosen by claudius-tune)")
except OSError:
    pass

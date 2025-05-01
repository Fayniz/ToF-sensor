#!/usr/bin/env python3

import sys
import signal
import time
from datetime import datetime

# Optional: adjust path if VL53L1X is not globally installed
# sys.path.insert(0, "build/lib.linux-armv7l-2.7/")

import VL53L1X

# Initialize sensor
tof = VL53L1X.VL53L1X(i2c_bus=1, i2c_address=0x29)
print("Python: Initialized")
tof.open()
print("Python: Opened")

# ROI scan options
def scan(scan_type="w"):
    if scan_type == "w":
        print("Scan: wide")
        return VL53L1X.VL53L1xUserRoi(0, 15, 15, 0)
    elif scan_type == "c":
        print("Scan: center")
        return VL53L1X.VL53L1xUserRoi(6, 9, 9, 6)
    elif scan_type == "t":
        print("Scan: top")
        return VL53L1X.VL53L1xUserRoi(6, 15, 9, 12)
    elif scan_type == "b":
        print("Scan: bottom")
        return VL53L1X.VL53L1xUserRoi(6, 3, 9, 0)
    elif scan_type == "l":
        print("Scan: left")
        return VL53L1X.VL53L1xUserRoi(0, 9, 3, 6)
    elif scan_type == "r":
        print("Scan: right")
        return VL53L1X.VL53L1xUserRoi(12, 9, 15, 6)
    else:
        print("Scan: wide (default)")
        return VL53L1X.VL53L1xUserRoi(0, 15, 15, 0)

# Use scan type from argument if provided
roi = scan(sys.argv[1]) if len(sys.argv) == 2 else scan("w")

# Apply ROI and start ranging
tof.set_user_roi(roi)
tof.start_ranging(1)  # Short range

# Handle Ctrl+C to safely stop sensor
def exit_handler(sig, frame):
    print("\nStopping VL53L1X...")
    tof.stop_ranging()
    tof.close()
    sys.exit(0)

signal.signal(signal.SIGINT, exit_handler)

# Main loop
while True:
    distance_mm = tof.get_distance()
    if distance_mm < 0:
        print("Error: {}".format(distance_mm))
    else:
        print("Distance: {:.1f} cm".format(distance_mm / 10.0))
    time.sleep(0.5)


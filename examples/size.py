#!/usr/bin/env python3
import sys
import signal
import time
import math
from datetime import datetime
import VL53L1X

# Initialize sensor
tof = VL53L1X.VL53L1X(i2c_bus=1, i2c_address=0x29)
print("Initialized VL53L1X sensor")
tof.open()
print("Sensor connection opened")

# Set SHORT distance mode (1.3m max) and 50ms timing budget
tof.set_distance_mode(VL53L1X.VL53L1xDistanceMode.SHORT)
tof.set_timing(timing_budget=50000, inter_measurement_period=50)  # 50ms timing, 50ms delay
print("Configured for SHORT distance mode (1.3m max) with 50ms timing budget")

# Define ROI regions - 16x16 SPAD array
# Each region is defined as (TopLeftX, TopLeftY, BottomRightX, BottomRightY)
def define_roi(region):
    regions = {
        "wide": VL53L1X.VL53L1xUserRoi(0, 15, 15, 0),  # Full FoV (27°)
        "center": VL53L1X.VL53L1xUserRoi(6, 9, 9, 6),   # Center (≈6°)
        # Horizontal edges (narrower zones)
        "left_edge": VL53L1X.VL53L1xUserRoi(0, 8, 2, 7),
        "right_edge": VL53L1X.VL53L1xUserRoi(13, 8, 15, 7),
        # Vertical edges (narrower zones)
        "top_edge": VL53L1X.VL53L1xUserRoi(7, 15, 8, 13),
        "bottom_edge": VL53L1X.VL53L1xUserRoi(7, 2, 8, 0),
    }
    return regions.get(region, regions["wide"])


# Handle Ctrl+C to safely stop sensor
def exit_handler(sig, frame):
    print("\nStopping VL53L1X...")
    tof.stop_ranging()
    tof.close()
    sys.exit(0)

signal.signal(signal.SIGINT, exit_handler)

# Constants for calculations
HORIZONTAL_FOV_DEGREES = 27  # Field of view of VL53L1X
VERTICAL_FOV_DEGREES = 27
HORIZONTAL_SPAD_COUNT = 16
VERTICAL_SPAD_COUNT = 16

def get_distance_for_roi(roi_name):
    """Get distance measurement for a specific ROI"""
    roi = define_roi(roi_name)
    tof.set_user_roi(roi)
    time.sleep(0.1)  # Brief delay for sensor to adjust
    
    # Take multiple measurements for reliability
    measurements = []
    for _ in range(5):
        distance = tof.get_distance()
        if distance > 0:  # Valid measurement
            measurements.append(distance)
        time.sleep(0.05)
    
    # Return average of valid measurements
    if measurements:
        return sum(measurements) / len(measurements)
    else:
        return -1

def detect_object_edges():
    """Detect object edges by scanning across ROIs"""
    print("\nScanning for object dimensions...")
    
    # Start with wide ROI to detect if object is present
    tof.start_ranging()  # Already set to SHORT mode
    wide_distance = get_distance_for_roi("wide")
    
    if wide_distance <= 0:
        print("No valid distance detected. Check sensor position.")
        return None, None
    
    # Background distance (assume this is the distance to wall/background)
    print(f"Reference distance: {wide_distance/10:.1f} cm")
    
    # Set threshold for edge detection (adjust based on your environment)
    edge_threshold_pct = 15
    threshold_mm = wide_distance * edge_threshold_pct / 100
    
    # Horizontal scan (width estimation)
    horizontal_regions = ["left_edge", "left_mid", "center", "right_mid", "right_edge"]
    horizontal_distances = []
    
    print("\nHorizontal scan:")
    for region in horizontal_regions:
        dist = get_distance_for_roi(region)
        horizontal_distances.append(dist)
        print(f"  {region}: {dist/10:.1f} cm")
    
    # Vertical scan (height estimation)
    vertical_regions = ["top_edge", "top_mid", "center", "bottom_mid", "bottom_edge"]
    vertical_distances = []
    
    print("\nVertical scan:")
    for region in vertical_regions:
        dist = get_distance_for_roi(region)
        vertical_distances.append(dist)
        print(f"  {region}: {dist/10:.1f} cm")
    
    # Find horizontal edges
    left_edge_idx = -1
    right_edge_idx = -1
    
    for i in range(len(horizontal_distances) - 1):
        if abs(horizontal_distances[i] - horizontal_distances[i+1]) > threshold_mm:
            if left_edge_idx == -1:
                left_edge_idx = i
            else:
                right_edge_idx = i + 1
                break
    
    # Find vertical edges
    top_edge_idx = -1
    bottom_edge_idx = -1
    
    for i in range(len(vertical_distances) - 1):
        if abs(vertical_distances[i] - vertical_distances[i+1]) > threshold_mm:
            if top_edge_idx == -1:
                top_edge_idx = i
            else:
                bottom_edge_idx = i + 1
                break
    
    # Calculate width and height
    width = None
    height = None
    
    # Average distance to object (more accurate than wide measurement)
    object_distance = horizontal_distances[2]  # Center region
    
    if left_edge_idx != -1 and right_edge_idx != -1:
        angular_span = (right_edge_idx - left_edge_idx) * (HORIZONTAL_FOV_DEGREES / len(horizontal_regions))
        width = 2 * object_distance * math.tan(math.radians(angular_span) / 2)
    
    if top_edge_idx != -1 and bottom_edge_idx != -1:
        angular_span = (bottom_edge_idx - top_edge_idx) * (VERTICAL_FOV_DEGREES / len(vertical_regions))
        height = 2 * object_distance * math.tan(math.radians(angular_span) / 2)
    
    return width, height

def main():
    try:
        while True:
            user_input = input("\nPress Enter to scan object dimensions or 'q' to quit: ")
            if user_input.lower() == 'q':
                break
                
            width_mm, height_mm = detect_object_edges()
            
            if width_mm and height_mm:
                print(f"\nEstimated object dimensions:")
                print(f"  Width: {width_mm/10:.1f} cm")
                print(f"  Height: {height_mm/10:.1f} cm")
            else:
                print("\nCouldn't determine object dimensions. Try repositioning the object.")
                
    finally:
        tof.stop_ranging()
        tof.close()
        print("Sensor closed")

if __name__ == "__main__":
    main()e
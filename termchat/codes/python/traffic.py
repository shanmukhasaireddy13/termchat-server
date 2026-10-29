import sys
import time

# 1. Dependency Check
try:
    from gpiozero import LED
    GPIOZERO_AVAILABLE = True
except ImportError:
    GPIOZERO_AVAILABLE = False
    print("Notice: gpiozero package not found.")
    print("To install on Raspberry Pi:")
    print("  pip install gpiozero")
    print("  (or: sudo apt install python3-gpiozero)")
    print("Running in simulated terminal mode...\n")

# Pin definitions (BCM)
PIN_CONFIG = {
    1: {'R': 17, 'Y': 27, 'G': 22},
    2: {'R': 10, 'Y': 9,  'G': 11},
    3: {'R': 5,  'Y': 6,  'G': 13},
    4: {'R': 19, 'Y': 26, 'G': 21}
}

# Dummy LED class for non-RPi / simulated environments
class SimulatedLED:
    def __init__(self, pin):
        self.pin = pin
        self.state = False

    def on(self):
        self.state = True

    def off(self):
        self.state = False


roads = {}
hardware_active = False

if GPIOZERO_AVAILABLE:
    try:
        for r_id, p_map in PIN_CONFIG.items():
            roads[r_id] = {
                'R': LED(p_map['R']),
                'Y': LED(p_map['Y']),
                'G': LED(p_map['G'])
            }
        hardware_active = True
    except Exception as e:
        print(f"Hardware GPIO unavailable ({e}). Using simulated mode.\n")

if not hardware_active:
    for r_id, p_map in PIN_CONFIG.items():
        roads[r_id] = {
            'R': SimulatedLED(p_map['R']),
            'Y': SimulatedLED(p_map['Y']),
            'G': SimulatedLED(p_map['G'])
        }

# Timing Values
MIN_GREEN = 3
TIME_PER_CAR = 0.5
MAX_GREEN = 45
YELLOW_TIME = 2
BUFFER_TIME = 1


def get_green_duration(cars):
    return min(MIN_GREEN + (cars * TIME_PER_CAR), MAX_GREEN)


def set_all_red():
    for road in roads.values():
        road['G'].off()
        road['Y'].off()
        road['R'].on()


try:
    set_all_red()
    while True:
        print("\n--- 4-Way Traffic Light Controller ---")
        if not hardware_active:
            print("[Mode: Terminal Simulation]")
        else:
            print("[Mode: Physical GPIO Active]")

        car_counts = {}
        for i in range(1, 5):
            val = input(f"Enter vehicles on Road {i} (or 'q' to quit): ").strip().lower()
            if val == 'q':
                sys.exit(0)
            try:
                car_counts[i] = max(0, int(val))
            except ValueError:
                car_counts[i] = 0

        for active in range(1, 5):
            green_time = get_green_duration(car_counts[active])

            set_all_red()
            time.sleep(BUFFER_TIME)

            print(f"Road {active} -> GREEN ({green_time} sec) | Others: RED")
            roads[active]['R'].off()
            roads[active]['G'].on()
            time.sleep(green_time)

            print(f"Road {active} -> YELLOW ({YELLOW_TIME} sec)")
            roads[active]['G'].off()
            roads[active]['Y'].on()
            time.sleep(YELLOW_TIME)

except (KeyboardInterrupt, SystemExit):
    print("\nSystem Stopped.")
    for road in roads.values():
        road['R'].off()
        road['Y'].off()
        road['G'].off()

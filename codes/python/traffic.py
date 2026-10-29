import time
from gpiozero import LED

# LED Connections
roads = {
    1: {'R': LED(17), 'Y': LED(27), 'G': LED(22)},
    2: {'R': LED(10), 'Y': LED(9),  'G': LED(11)},
    3: {'R': LED(5),  'Y': LED(6),  'G': LED(13)},
    4: {'R': LED(19), 'Y': LED(26), 'G': LED(21)}
}

# Timing Values
MIN_GREEN = 3
TIME_PER_CAR = 0.5
MAX_GREEN = 45
YELLOW_TIME = 2
BUFFER_TIME = 1

# Calculate Green Time
def get_green_duration(cars):
    return min(MIN_GREEN + (cars * TIME_PER_CAR), MAX_GREEN)

# Turn all roads Red
def set_all_red():
    for road in roads.values():
        road['G'].off()
        road['Y'].off()
        road['R'].on()

try:
    while True:

        print("\n--- Traffic Light Controller ---")

        car_counts = {}

        for i in range(1,5):
            car_counts[i] = int(input(f"Enter vehicles on Road {i}: "))

        for active in range(1,5):

            greenTime = get_green_duration(car_counts[active])

            set_all_red()
            time.sleep(BUFFER_TIME)

            print(f"Road {active} -> GREEN ({greenTime} sec)")
            roads[active]['R'].off()
            roads[active]['G'].on()
            time.sleep(greenTime)

            print(f"Road {active} -> YELLOW")
            roads[active]['G'].off()
            roads[active]['Y'].on()
            time.sleep(YELLOW_TIME)

except KeyboardInterrupt:

    print("System Stopped")

    for road in roads.values():
        road['R'].off()
        road['Y'].off()
        road['G'].off()

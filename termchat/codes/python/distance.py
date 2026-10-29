import sys
import time

# 1. Dependency Check
try:
    import RPi.GPIO as GPIO
except ImportError:
    print("Missing required package: RPi.GPIO")
    print("Run: pip install RPi.GPIO")
    print("On Raspberry Pi OS: sudo apt install python3-rpi.gpio")
    sys.exit(1)

TRIG = 23
ECHO = 24
BUZZER = 18
THRESHOLD = 10

try:
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(TRIG, GPIO.OUT)
    GPIO.setup(ECHO, GPIO.IN)
    GPIO.setup(BUZZER, GPIO.OUT)
    GPIO.output(TRIG, False)
    GPIO.output(BUZZER, False)
except Exception as e:
    print(f"GPIO initialization error: {e}")
    print("Ensure this script is running on a Raspberry Pi with GPIO access.")
    sys.exit(1)

print("Ultrasonic Sensor HC-SR04 Active")
print("Press Ctrl+C to stop.")
time.sleep(1)

try:
    while True:
        # Trigger 10us ultrasonic pulse
        GPIO.output(TRIG, True)
        time.sleep(0.00001)
        GPIO.output(TRIG, False)

        pulse_start = time.time()
        pulse_end = pulse_start

        # Timeout protection (0.04s max wait = ~6.8m range limit)
        timeout = time.time() + 0.04
        while GPIO.input(ECHO) == 0:
            pulse_start = time.time()
            if pulse_start > timeout:
                break

        timeout = time.time() + 0.04
        while GPIO.input(ECHO) == 1:
            pulse_end = time.time()
            if pulse_end > timeout:
                break

        pulse_duration = pulse_end - pulse_start
        if pulse_duration <= 0 or pulse_duration >= 0.04:
            print("Distance: Out of range or sensor timeout")
            GPIO.output(BUZZER, False)
            time.sleep(0.5)
            continue

        distance_cm = round(pulse_duration * 17150, 2)
        distance_in = round(distance_cm / 2.54, 2)

        print(f"Distance: {distance_cm} cm | {distance_in} in")

        if distance_cm <= THRESHOLD:
            GPIO.output(BUZZER, True)
        else:
            GPIO.output(BUZZER, False)

        time.sleep(0.5)

except KeyboardInterrupt:
    print("\nMeasurement Stopped by user.")
finally:
    GPIO.output(BUZZER, False)
    GPIO.cleanup()

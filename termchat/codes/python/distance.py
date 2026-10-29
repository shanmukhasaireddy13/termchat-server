import RPi.GPIO as GPIO
import time

TRIG = 23
ECHO = 24
BUZZER = 18
THRESHOLD = 10

GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)
GPIO.setup(BUZZER, GPIO.OUT)
GPIO.output(TRIG, False)
GPIO.output(BUZZER, False)

time.sleep(2)

try:
    while True:
        GPIO.output(TRIG, True)
        time.sleep(0.00001)
        GPIO.output(TRIG, False)

        while GPIO.input(ECHO) == 0:
            pulse_start = time.time()
        while GPIO.input(ECHO) == 1:
            pulse_end = time.time()

        pulse_duration = pulse_end - pulse_start
        distance_cm = round(pulse_duration * 17150, 2)
        distance_in = round(distance_cm / 2.54, 2)

        print(f"Distance: {distance_cm} cm | {distance_in} in")

        if distance_cm <= THRESHOLD:
            GPIO.output(BUZZER, True)
        else:
            GPIO.output(BUZZER, False)

        time.sleep(0.5)

except KeyboardInterrupt:
    print("Measurement Stopped")
    GPIO.cleanup()

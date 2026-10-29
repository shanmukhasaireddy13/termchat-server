// -----------------------------------------
// Arduino Smart Car Parking System
// -----------------------------------------

// Pin Definitions
const int entrySensor = 2;   // Entry IR Sensor
const int exitSensor  = 3;   // Exit IR Sensor
const int buzzer      = 4;   // Buzzer

// Parking Variables
int freeSpace = 10;          // Total available parking spaces

// Flags to avoid multiple counts
bool carEntering = false;
bool carExiting = false;

void printStatus() {
  Serial.print("Available Spaces: ");
  Serial.println(freeSpace);

  if (freeSpace == 0) {
    Serial.println("STATUS : PARKING FULL");
  }

  Serial.println("------------------------------");
}

void setup() {
  Serial.begin(9600);

  pinMode(entrySensor, INPUT);
  pinMode(exitSensor, INPUT);
  pinMode(buzzer, OUTPUT);

  digitalWrite(buzzer, LOW);

  Serial.println("----- Smart Parking System -----");
  printStatus();
}

void loop() {
  // Read IR Sensors
  int entryState = digitalRead(entrySensor);
  int exitState  = digitalRead(exitSensor);

  // ---------------- Entry Section ----------------
  if (entryState == LOW && !carEntering) {
    carEntering = true;

    if (freeSpace > 0) {
      freeSpace--;
      Serial.println("Car Entered");
      printStatus();
    }
    else {
      Serial.println("Parking Full!");
      digitalWrite(buzzer, HIGH);
      delay(1000);
      digitalWrite(buzzer, LOW);
    }
  }

  // Reset Entry Flag
  if (entryState == HIGH) {
    carEntering = false;
  }

  // ---------------- Exit Section ----------------
  if (exitState == LOW && !carExiting) {
    carExiting = true;

    if (freeSpace < 10) {
      freeSpace++;
      Serial.println("Car Exited");
      printStatus();
    }
    else {
      Serial.println("Parking Already Empty");
    }
  }

  // Reset Exit Flag
  if (exitState == HIGH) {
    carExiting = false;
  }

  delay(50);
}

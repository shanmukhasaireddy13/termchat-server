// -------------------------------------------------------------
// Arduino Maze Solving Robot Using Ultrasonic Sensor
// -------------------------------------------------------------

#define ENB 5
#define IN1 7
#define IN2 8
#define IN3 9
#define IN4 11
#define ENA 6

#define TRIG_PIN A0
#define ECHO_PIN A1

const int SPEED = 120;
const int TURN_SPEED = 140;
const int SAFE_DISTANCE = 25;

const int TURN_TIME = 500;
const int UTURN_TIME = 1000;

void setup() {
  pinMode(ENB, OUTPUT);
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);
  pinMode(ENA, OUTPUT);

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  stopBot();
  delay(2000);
}

void loop() {
  int front = getDistance();

  if (front > SAFE_DISTANCE) {
    forward();
  }

  else {
    stopBot();
    delay(200);

    turnLeft();
    delay(TURN_TIME);

    stopBot();
    delay(100);

    int left = getDistance();

    turnRight();
    delay(TURN_TIME);

    stopBot();
    delay(100);

    turnRight();
    delay(TURN_TIME);

    stopBot();
    delay(100);

    int right = getDistance();

    turnLeft();
    delay(TURN_TIME);

    stopBot();
    delay(100);

    if (left > SAFE_DISTANCE && left >= right) {
      turnLeft();
      delay(TURN_TIME);
    }

    else if (right > SAFE_DISTANCE) {
      turnRight();
      delay(TURN_TIME);
    }

    else {
      turnRight();
      delay(UTURN_TIME);
    }

    stopBot();
    delay(100);
  }
}

int getDistance() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);

  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);

  digitalWrite(TRIG_PIN, LOW);

  long duration = pulseIn(ECHO_PIN, HIGH, 30000);

  if (duration == 0) {
    return 400;
  }

  int distance = duration * 0.034 / 2;

  return distance;
}

void forward() {
  analogWrite(ENA, SPEED);
  analogWrite(ENB, SPEED);

  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);

  digitalWrite(IN3, LOW);
  digitalWrite(IN4, HIGH);
}

void turnRight() {
  analogWrite(ENA, TURN_SPEED);
  analogWrite(ENB, TURN_SPEED);

  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);

  digitalWrite(IN3, HIGH);
  digitalWrite(IN4, LOW);
}

void turnLeft() {
  analogWrite(ENA, TURN_SPEED);
  analogWrite(ENB, TURN_SPEED);

  digitalWrite(IN1, LOW);
  digitalWrite(IN2, HIGH);

  digitalWrite(IN3, LOW);
  digitalWrite(IN4, HIGH);
}

void stopBot() {
  analogWrite(ENA, 0);
  analogWrite(ENB, 0);

  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, LOW);
}

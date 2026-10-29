// -------------------------------------------------------------
// Arduino Square Motion Controller (L298N Motor Driver)
// -------------------------------------------------------------

#define ENB 5
#define IN1 7
#define IN2 8
#define IN3 9
#define IN4 11
#define ENA 6

int speedL = 150;
int speedR = 150;

int forwardTime = 2000;
int turnTime = 650;

void setup() {
  pinMode(ENB, OUTPUT);
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);
  pinMode(ENA, OUTPUT);

  stopBot();
  delay(2000);
}

void loop() {
  for (int i = 0; i < 4; i++) {
    forward();
    delay(forwardTime);

    stopBot();
    delay(300);

    turnRight();
    delay(turnTime);

    stopBot();
    delay(300);
  }

  while (true) {
    stopBot();
  }
}

void forward() {
  analogWrite(ENA, speedL);
  analogWrite(ENB, speedR);

  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);

  digitalWrite(IN3, LOW);
  digitalWrite(IN4, HIGH);
}

void turnRight() {
  analogWrite(ENA, speedL);
  analogWrite(ENB, speedR);

  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);

  digitalWrite(IN3, HIGH);
  digitalWrite(IN4, LOW);
}

void stopBot() {
  analogWrite(ENA, 0);
  analogWrite(ENB, 0);

  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, LOW);
}

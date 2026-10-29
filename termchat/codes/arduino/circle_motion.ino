// -------------------------------------------------------------
// Arduino Circle Motion Controller (L298N Motor Driver)
// -------------------------------------------------------------

#define ENB 5
#define IN1 7
#define IN2 8
#define IN3 9
#define IN4 11
#define ENA 6

int leftSpeed = 170;
int rightSpeed = 80;
int circleTime = 4500;

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
  circle();

  stopBot();

  while (true) {
    stopBot();
  }
}

void circle() {
  analogWrite(ENA, leftSpeed);
  analogWrite(ENB, rightSpeed);

  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);

  digitalWrite(IN3, LOW);
  digitalWrite(IN4, HIGH);

  delay(circleTime);
}

void stopBot() {
  analogWrite(ENA, 0);
  analogWrite(ENB, 0);

  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, LOW);
}

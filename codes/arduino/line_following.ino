// -------------------------------------------------------------
// Arduino Line Following Robot (3-Channel IR Line Tracking)
// -------------------------------------------------------------

#define LT_L 2
#define LT_M 4
#define LT_R 10

#define ENB 5
#define IN1 7
#define IN2 8
#define IN3 9
#define IN4 11
#define ENA 6

const int BASE_SPEED = 100;
const int SLOW_SPEED = 20;
const int FAST_SPEED = 140;
const int SEARCH_SPEED = 120;

void setup() {
  pinMode(LT_L, INPUT);
  pinMode(LT_M, INPUT);
  pinMode(LT_R, INPUT);

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
  int leftState = digitalRead(LT_L);
  int middleState = digitalRead(LT_M);
  int rightState = digitalRead(LT_R);

  if (leftState == LOW &&
      middleState == HIGH &&
      rightState == LOW) {
    forward(BASE_SPEED, BASE_SPEED);
  }

  else if (leftState == HIGH &&
           rightState == LOW) {
    forward(SLOW_SPEED, FAST_SPEED);
  }

  else if (leftState == LOW &&
           rightState == HIGH) {
    forward(FAST_SPEED, SLOW_SPEED);
  }

  else if (leftState == LOW &&
           middleState == LOW &&
           rightState == LOW) {
    spinSearchRight();
  }

  else if (leftState == HIGH &&
           middleState == HIGH &&
           rightState == HIGH) {
    forward(BASE_SPEED, BASE_SPEED);
  }
}

void forward(int speedLeft, int speedRight) {
  analogWrite(ENA, speedLeft);
  analogWrite(ENB, speedRight);

  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);

  digitalWrite(IN3, LOW);
  digitalWrite(IN4, HIGH);
}

void spinSearchRight() {
  analogWrite(ENA, SEARCH_SPEED);
  analogWrite(ENB, SEARCH_SPEED);

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

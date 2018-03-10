#include "AlarmClock.h"

// Arduino pins
int CA_1 = 7; // 12;
int CA_2 = 2; // 11;
int CA_3 = 3; // 10;
int CA_4 = 8; // 9;
int clk = 4; // 6;
int latch = 5;
int data = 6; // 4;
int RELAY = 11; // 3;
int LBUTTON = 9; // 2;
int RBUTTON = 10; // 7;
int BUZZER = 13;

int UNIQUE_LEDS = 7;
int NUM_LEDS = 12;
int LEDS[12] = {A0, A1, A2, A3, A4, A5, 12, A5, A4, A3, A2, A1};
int led_count = 0;
int NUM_LED_CYCLES = 4;
int LED_CYCLES[4] = {0, 1, 2, 0};
int LED_CYCLE_VALUES[4] = {HIGH, HIGH, HIGH, LOW};
int led_cycle_count = 0;

// Current digit being output
int count = 0;
// Pins for each digit
int CAS[4] = {CA_1, CA_2, CA_3, CA_4};
//byte combinations for each number 0-9
byte numbers[10] {
	B11111100,
	B01100000,
	B11011010,
	B11110010,
	B01100110,
	B10110110,
	B10111110,
	B11100000,
	B11111110,
	B11110110};
byte BLANK = B00000000;

// Delay per loop, the value is the degree of fine tuning for the clock
int del = 5;
int MAX_SYNC_INTERVAL = 10 * SECS_PER_MIN;

// An array to store the received serial data
const byte numChars = 32;
char receivedChars[numChars];
boolean newData = false;

// Various states
boolean alternatingSeconds = true;
boolean sentL = false;
boolean sentR = false;
boolean relay = false;
boolean buzzer = false;
boolean lights = false;

void recvWithEndMarker();
void showNewData();
int get_number(int digit);
void set_number(int digit, int value);
void cathode_high();
void add();
void updateOutputs();
time_t requestSync();

void setup() {
  pinMode(RELAY, OUTPUT);
  for (int i=0; i < UNIQUE_LEDS; i++) {
    pinMode(LEDS[i], OUTPUT);
  }
  pinMode(LBUTTON, INPUT_PULLUP);
  pinMode(RBUTTON, INPUT_PULLUP);
  pinMode(CA_1, OUTPUT);
  pinMode(CA_2, OUTPUT);
  pinMode(CA_3, OUTPUT);
  pinMode(CA_4, OUTPUT);
  pinMode(clk, OUTPUT);
  pinMode(latch, OUTPUT);
  pinMode(data, OUTPUT);
  digitalWrite(CA_1, HIGH);
  digitalWrite(CA_2, HIGH);
  digitalWrite(CA_3, HIGH);
  digitalWrite(CA_4, HIGH);
  digitalWrite(RELAY, LOW);
  Serial.begin(9600);
  Timer1.initialize(1000000); // set a timer of length 1000000 microseconds (or 1 sec)
  Timer1.attachInterrupt( add ); // attach the service routine here
  setSyncProvider( requestSync );
  setSyncInterval(MAX_SYNC_INTERVAL);
}

void loop() {
  if (digitalRead(LBUTTON) == LOW) {
    if (!sentL) {
      Serial.println("L");
      sentL = true;
    }
  } else {
    sentL = false;
  }
  if (digitalRead(RBUTTON) == LOW) {
    if (!sentR) {
      Serial.println("R");
      sentR = true;
    }
  } else {
    sentR = false;
  }

  recvWithEndMarker();
  showNewData();

  set_number(count, get_number(count));
  delay(del);//delay 5ms

  count++;
  if (count == 4) {
    count = 0;

    if (lights) {
      digitalWrite(
          LEDS[(led_count + LED_CYCLES[led_cycle_count]) % NUM_LEDS],
          LED_CYCLE_VALUES[led_cycle_count]);
    }
    led_cycle_count++;
    if (led_cycle_count == NUM_LED_CYCLES) {
      led_cycle_count = 0;
      led_count++;
      if (led_count == NUM_LEDS) {
        led_count = 0;
      }
    }
  }
}

void recvWithEndMarker() {
	static byte ndx = 0;
	char endMarker = '\n';
	char rc;

	while (Serial.available() > 0 && newData == false) {
		rc = Serial.read();

		if (rc != endMarker) {
			receivedChars[ndx] = rc;
			ndx++;
			if (ndx >= numChars) {
				ndx = numChars - 1;
			}
		} else {
			receivedChars[ndx] = '\0'; // terminate the string
			ndx = 0;
			newData = true;
		}
	}
}

void showNewData() {
	if (newData == true) {
		newData = false;
		// Sync Arduino clock to the time received on the serial port
    setTime(
        (receivedChars[8] - '0') * 10 + receivedChars[9] - '0',
        (receivedChars[10] - '0') * 10 + receivedChars[11] - '0',
        (receivedChars[12] - '0') * 10 + receivedChars[13] - '0',
        (receivedChars[6] - '0') * 10 + receivedChars[7] - '0',
        (receivedChars[4] - '0') * 10 + receivedChars[5] - '0',
        (receivedChars[0] - '0') * 1000 + (receivedChars[1] - '0') * 100
        + (receivedChars[2] - '0') * 10 + receivedChars[3] - '0');
    if (receivedChars[14] != '\0') {
      if (receivedChars[14] == '1') {
        relay = true;
      } else {
        relay = false;
      }
      if (receivedChars[15] != '\0') {
        if (receivedChars[15] == '1') {
          buzzer = true;
        } else {
          buzzer = false;
        }
        if (receivedChars[16] != '\0') {
          if (receivedChars[16] == '1') {
            lights = true;
          } else {
            lights = false;
            for (int i=0; i < UNIQUE_LEDS; i++) {
              digitalWrite(LEDS[i], LOW);
            }
          }
        }
      }
    }
    updateOutputs();
	}
}

int get_number(int digit) {
  int myhours;
  int myminutes;
  switch (digit) {
  case 0:
  case 1:
    myhours = hourFormat12();
    return digit == 0 ? myhours / 10 : myhours % 10;
    break;
  case 2:
  case 3:
    myminutes = minute();
    return digit == 2 ? myminutes / 10 : myminutes % 10;
    break;
  default:
    return 0;
  }
}

void set_number(int digit, int value) {
  cathode_high(); //black screen
  if (timeStatus() != timeSet && alternatingSeconds) {
    return;
  }
  if (digit != 0 || value > 0) {
    digitalWrite(latch, LOW); //put the shift register to read
    shiftOut(data, clk, LSBFIRST,
        digit == 1 ? numbers[value] | B00000001 : numbers[value]); //send the data
    digitalWrite(CAS[digit], LOW); //turn on the relevent digit
    digitalWrite(latch, HIGH); //put the shift register to write mode
  }
}

void cathode_high() { //turn off all 4 digits
  digitalWrite(CA_1, HIGH);
  digitalWrite(CA_2, HIGH);
  digitalWrite(CA_3, HIGH);
  digitalWrite(CA_4, HIGH);
}

void writeCurrentTime() {
  char currentTime[15];
  time_t n = now();
  sprintf(currentTime, "%04i%02i%02i%02i%02i%02i",
      year(n), month(n), day(n), hour(n), minute(n), second(n));
  Serial.println(currentTime);
}

void add()
{
  if (alternatingSeconds) {
    alternatingSeconds = false;
  } else {
    alternatingSeconds = true;
  }
  if (second() == 0) {
    writeCurrentTime();
  }
  updateOutputs();
}

void updateOutputs() {
  if (relay) {
    digitalWrite(RELAY, HIGH);
  } else {
    digitalWrite(RELAY, LOW);
  }
  if (buzzer) {
    // tone(BUZZER, 523, 1100);
    tone(BUZZER, 1047, 1100);
  } else {
    noTone(BUZZER);
  }
}

time_t requestSync()
{
  //writeCurrentTime();
  return 0; // the time will be sent later in response to serial mesg
}

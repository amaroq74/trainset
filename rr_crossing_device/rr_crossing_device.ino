
#include <Servo.h>

Servo ServoA;
Servo ServoB;

const unsigned int SensorCnt  = 4;
const unsigned int ServoCnt = 2;
const unsigned int LedCnt   = 4;
const unsigned int SensorPin[SensorCnt] = {8, 11, 12, 13};
const unsigned int ServoPin[ServoCnt] = {9, 10};
const unsigned int LedPin[LedCnt] = {4, 5, 6, 7};

unsigned int x;
unsigned int servoValue[ServoCnt];
unsigned int ledValue;
unsigned int sensorValue[SensorCnt];
unsigned int newValue[SensorCnt];
unsigned int send;
unsigned int rxCount;
unsigned int ledSet;
unsigned int servoSet[ServoCnt];
unsigned long lastSend;

int ret;
char c;
char mark[20];
char rxBuffer[50];
char txBuffer[50];

Servo rrServo[ServoCnt];

void setup() {
  Serial.begin(9600);

   for(x=0; x < ServoCnt; x++) {
      rrServo[x].attach(ServoPin[x]);
      servoValue[x] = 90;
      rrServo[x].write(servoValue[x]);
   }

   for(x=0; x < LedCnt; x++) {
      pinMode(LedPin[x], OUTPUT);
      digitalWrite(LedPin[x], HIGH);
   }
   ledValue = 0;

   for(x=0; x < SensorCnt; x++) {
      pinMode(SensorPin[x], INPUT_PULLUP);
      sensorValue[x] = 0;
      newValue[x] = 0;
   }

   rxCount = 0;
}

void loop(){

   for(x=0; x < ServoCnt; x++) {
      if (servoValue[x] > 180) servoValue[x] = 180;
      rrServo[x].write(servoValue[x]);
   }

   if ( ledValue == 1 ) {
      for (x=0; x < LedCnt; x += 2) {
         digitalWrite(LedPin[x], HIGH);
         digitalWrite(LedPin[x+1], LOW);
      }
   }

   else if ( ledValue == 2 ) {
      for (x=0; x < LedCnt; x += 2) {
         digitalWrite(LedPin[x], LOW);
         digitalWrite(LedPin[x+1], HIGH);
      }
   }

   else {
      for (x=0; x < LedCnt; x++) digitalWrite(LedPin[x], HIGH);
   }

   send = 0;

   for (x=0; x < SensorCnt; x++) {
      if (digitalRead(SensorPin[x]) == 0) newValue[x] = 1;
      else newValue[x] = 0;

      if (newValue[x] != sensorValue[x]) send = 1;
      sensorValue[x] = newValue[x];
   }

   if ( (millis() - lastSend) > 1000 ) send = 1;

   if (send) {
      sprintf(txBuffer,"Status %i %i %i %i\n",sensorValue[0],sensorValue[1],sensorValue[2],sensorValue[3]);
      Serial.write(txBuffer);
      lastSend = millis();
   }

   // Get serial data
   while (Serial.available()) {
      if ( rxCount == 49 ) rxCount = 0;

      c = Serial.read();
      rxBuffer[rxCount++] = c;
      rxBuffer[rxCount] = '\0';
   }

   // Check for incoming message
   if ( rxCount > 6 && rxBuffer[rxCount-1] == '\n') {

      // Parse string
      ret = sscanf(rxBuffer,"%s %i %i %i", mark, &ledSet, &(servoSet[0]), &(servoSet[1]));

      if (ret == 4 && strcmp(mark,"set")) {
         ledValue = ledSet;
         for(x=0; x < ServoCnt; x++) servoValue[x] = servoSet[x];
      }
      rxCount = 0;
   }
}


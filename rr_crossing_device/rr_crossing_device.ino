
#include <Servo.h>

Servo ServoA;
Servo ServoB;

const unsigned int SensorCnt  = 4;
const unsigned int SensorPin[SensorCnt] = {8, 11, 12, 13};
const unsigned long SensorOffPeriod = 500;
const unsigned long SensorOnPeriod = 100;

const unsigned long SendPeriod = 1000;
const unsigned long CrossPeriod = 3000;

const unsigned int LedCnt   = 4;
const unsigned long LedPeriod = 250;
const unsigned int LedPin[LedCnt] = {4, 5, 6, 7};

const unsigned int ServoCnt = 2;
const unsigned int ServoPin[ServoCnt] = {9, 10};
const unsigned int ServoUp[ServoCnt] = {120,120};
const unsigned int ServoDown[ServoCnt] = {85,82};

unsigned int x;
unsigned long currTime;

unsigned int sensorRaw[SensorCnt];
unsigned int sensorValue[SensorCnt];
unsigned long sensorTime[SensorCnt];
unsigned int sensorsOn;

unsigned int crossState;
unsigned long crossTime;

unsigned int ledState;
unsigned long ledTime;

unsigned int doSend;
unsigned long lastSend;
char txBuffer[50];

Servo rrServo[ServoCnt];

void setup() {
  Serial.begin(9600);

   for(x=0; x < ServoCnt; x++) {
      rrServo[x].attach(ServoPin[x]);
      rrServo[x].write(ServoUp[x]);
   }

   for(x=0; x < LedCnt; x++) {
      pinMode(LedPin[x], OUTPUT);
      digitalWrite(LedPin[x], HIGH);
   }

   ledState = 0;
   ledTime = millis();
   crossState = 0;
   crossTime = millis();

   for(x=0; x < SensorCnt; x++) {
      pinMode(SensorPin[x], INPUT_PULLUP);
      sensorTime[x] = millis();
      sensorValue[x] = 0;
      sensorRaw[x] = 0;
   }
   sensorsOn = 0;
   lastSend = millis();
}

void loop(){
   doSend = 0;
   currTime = millis();

   //////////////////////////////////
   // Update sensor values
   //////////////////////////////////
   sensorsOn = 0;

   for (x=0; x < SensorCnt; x++) {

      // Reset time anytime the sensor is on
      if (digitalRead(SensorPin[x]) == 0) {
         if (sensorRaw[x] == 0) sensorTime[x] = currTime;
         sensorRaw[x] = 1;
      }
      else {
         if (sensorRaw[x] == 1) sensorTime[x] = currTime;
         sensorRaw[x] = 0;
      }

      // Change
      if (sensorRaw[x] != sensorValue[x]) {

         // Turning On
         if ( sensorRaw[x] == 1 && ( (currTime - sensorTime[x]) > SensorOnPeriod ) ) {
            doSend = 1;
            sensorValue[x] = 1;
         }

         // Turning off after hold time
         else if ( sensorRaw[x] == 0 && ( (currTime - sensorTime[x]) > SensorOffPeriod ) ) {
            doSend = 1;
            sensorValue[x] = 0;
         }
      }

      if ( sensorValue[x] ) sensorsOn = 1;
   }

   //////////////////////////////////
   // Update Crossing State
   //////////////////////////////////

   // Update cross on timestamp
   if ( sensorsOn ) crossTime = currTime;

   // Sensor state does not match cross state
   if ( sensorsOn != crossState ) {

      // Turning on
      if ( sensorsOn ) {
         crossState = 1;
         doSend = 1;
      }

      // Turning off after hold time
      else if ( (currTime - crossTime) > CrossPeriod ) {
         crossState = 0;
         doSend = 1;
      }
   }

   //////////////////////////////////
   // Update servo Values
   //////////////////////////////////
   for(x=0; x < ServoCnt; x++) {
      if (crossState) rrServo[x].write(ServoDown[x]);
      else rrServo[x].write(ServoUp[x]);
   }

   //////////////////////////////////
   // Update LED State
   //////////////////////////////////

   // LEDs On
   if ( crossState ) {

      // Transition
      if ( (currTime - ledTime) > LedPeriod )  {
         ledTime = currTime;

         if ( ledState ) {
            for(x=0; x < LedCnt; x += 2) {
               digitalWrite(LedPin[x], HIGH);
               digitalWrite(LedPin[x+1], LOW);
            }
            ledState = 0;
         }

         else {
            for(x=0; x < LedCnt; x += 2) {
               digitalWrite(LedPin[x], LOW);
               digitalWrite(LedPin[x+1], HIGH);
            }
            ledState = 1;
         }
      }
   }

   // LEDs Off
   else {
      for (x=0; x < LedCnt; x++) digitalWrite(LedPin[x], HIGH);
      ledTime = currTime;
   }

   if ( (currTime - lastSend) > SendPeriod ) doSend = 1;

   if (doSend) {
      sprintf(txBuffer,"Status %i %i %i %i %i\n",sensorValue[0],sensorValue[1],sensorValue[2],sensorValue[3],crossState);
      Serial.write(txBuffer);
      lastSend = currTime;
   }

}


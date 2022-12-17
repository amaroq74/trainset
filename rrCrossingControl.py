#!/usr/bin/env python

import paho.mqtt.client as mqtt
import queue
import time
import threading
import serial


class RrCrossing(object):


    def __init__(self):
        self._sensors = [False] * 4
        self._runEnable = False
        self._serialThread = threading.Thread(target=self._runSerial)
        self._mqttThread = threading.Thread(target=self._runMqtt)
        self._contThread = threading.Thread(target=self._runControl)
        self._mqttQueue = queue.SimpleQueue()
        self._servo = [90] * 2
        self._led = 0


    def start(self):
        self._runEnable = True
        self._contThread.start()
        self._serialThread.start()
        self._mqttThread.start()
        self._mqttQueue.put(True)


    def stop(self):
        self._runEnable = False
        self._serialThread.join()
        self._mqttThread.join()
        self._contThread.join()


    def _rxSensors(self, values):
        update = False

        for x in range(len(values)):

            if self._sensors[x] != values[x]:
                self._sensors[x] = values[x]
                update = True

        if update:
            self._mqttQueue.put(True)


    def _runMqtt(self):
        client = None

        while self._runEnable:

            if client is None:

                print("Connecting to mqtt server")
                client = mqtt.Client("RrCrossing")
                client.connect('172.16.20.1')

            # Process Sensor Updates
            if self._mqttQueue.empty() is False:
                work = self._mqttQueue.get_nowait()

                if work:
                    for x in range(len(self._sensors)):
                        client.publish(f"rr_cross/status/sense{x}", self._sensors[x])

            client.loop()
            time.sleep(.1)


    def _runSerial(self):

        while self._runEnable:
            try:
                with serial.Serial("/dev/ttyACM0", 9600) as s:

                    while self._runEnable:
                        line = s.readline().decode('UTF-8')
                        fields = line.rstrip().split(' ')

                        if len(fields) == 5 and fields[0] == 'Status':
                            values = [True if fields[x] != "0" else False for x in range(1,len(fields))]
                            self._rxSensors(values)

                        s.write(f"set {self._led} {self._servo[0]} {self._servo[1]}".encode('UTF-8'))

            except Exception as e:
                print(f"Serial Error: {e}")


    def _runControl(self):

        while self._runEnable:


            time.sleep(.1)






rr = RrCrossing()

rr.start()

try:
    while True:
        time.sleep(0.5)
except KeyboardInterrupt:
    print("Got cntrl-c, exiting")

rr.stop()

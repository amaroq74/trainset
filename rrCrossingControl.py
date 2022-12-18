#!/usr/bin/env python

import paho.mqtt.client as mqtt
import queue
import time
import threading
import serial

SensorStates = {'0': 'false',
                '1': 'true'}

SignalStates = {'0': 'green',
                '1': 'red'}

class RrCrossing(object):


    def __init__(self):
        self._sensors = ['unknown'] * 4
        self._rrCross = 'unknown'
        self._runEnable = False
        self._serialThread = threading.Thread(target=self._runSerial)
        self._mqttThread = threading.Thread(target=self._runMqtt)
        self._mqttQueue = queue.SimpleQueue()


    def start(self):
        self._runEnable = True
        self._serialThread.start()
        self._mqttThread.start()


    def stop(self):
        self._runEnable = False
        self._serialThread.join()
        self._mqttThread.join()


    def _runSerial(self):

        while self._runEnable:
            try:
                with serial.Serial("/dev/ttyACM0", 9600) as s:

                    while self._runEnable:
                        line = s.readline().decode('UTF-8')
                        fields = line.rstrip().split(' ')

                        if len(fields) == 6 and fields[0] == 'Status':
                            for x in range(4):

                                if self._sensors[x] != SensorStates[fields[x+1]]:
                                    self._sensors[x] = SensorStates[fields[x+1]]
                                    self._mqttQueue.put(f'<fb id="Sense {x+1}" state="{self._sensors[x]}"/>')

                            if self._rrCross != SignalStates[fields[5]]:
                                self._rrCross = SignalStates[fields[5]]
                                self._mqttQueue.put(f'<sg id="Cross" cmd="{self._rrCross}"/>')

                            print(f"Got Data: Sensors: {self._sensors}, Cross: {self._rrCross}")

            except Exception as e:
                print(f"Serial Error: {e}")


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
                    print(f"Sending: {work}")
                    client.publish(f"rocrail/service/client", work)

            client.loop()
            time.sleep(.1)


rr = RrCrossing()

rr.start()

try:
    while True:
        time.sleep(0.5)
except KeyboardInterrupt:
    print("Got cntrl-c, exiting")

rr.stop()

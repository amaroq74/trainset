#!/usr/bin/env python

import paho.mqtt.client as mqtt
import queue
import time
import threading
import xml.etree.ElementTree as etree

class TrainSetInterface(object):

    def __init__(self):

        self._queue = queue.SimpleQueue()
        self._thread = threading.Thread(target=self._run)
        self._runEnable = False
        self._name = 'rocrail_gw'
        self._power = False
        self._switch = {'City Loop'     : 'Closed',
                        'Mountain Loop' : 'Closed',
                        'Crossover'     : 'Closed',
                        'Mountain Yard' : 'Closed',
                        'Cement Plant'  : 'Closed',
                        'Coal Mine'     : 'Closed',
                        'Loco Yard'     : 'Closed',
                        'Middle Yard'   : 'Closed',
                        'Main Yard 1'   : 'Closed',
                        'Main Yard 2'   : 'Closed',
                        'Main Yard 3'   : 'Closed',
                        'Main Yard 4'   : 'Closed',
                        'Main Yard 5'   : 'Closed',
                        'Main Yard 6'   : 'Closed',
                        'River Yard 1'  : 'Closed',
                        'River Yard 2'  : 'Closed' }

    def start(self):
        self._runEnable = True
        self._thread.start()

    def stop(self):
        self._runEnable = False
        self._thread.join()

    def _rocrailRx(self, payload):
        tree = etree.fromstring(payload)

        if tree.tag == 'state':
            self._power = tree.get('power') == 'true'
            self._queue.put({'dir': 'sd', 'key': 'power', 'value' : self._power})

        elif tree.tag == 'sw' and tree.get('state') is not None:
            sid = tree.get('id')
            sstate = 'Thrown' if tree.get('state') == 'turnout'  else 'Closed'
            self._switch[sid] = sstate
            self._queue.put({'dir': 'sd', 'key': sid, 'value' : sstate})

        else:
            #print(f"Other message: {payload}")
            pass

    def _streamRx(self, topic, payload):

        if topic == "rocrail_gw/command/power":
            if payload == "True":
                self._queue.put({'dir': 'rr', 'key': 'power', 'value' : 'true'})
            else:
                self._queue.put({'dir': 'rr', 'key': 'power', 'value' : 'false'})

        else:
            sw = topic[len("rocrail_gw/command/"):]
            if sw in self._switch:
                if self._switch[sw] == 'Thrown':
                    self._queue.put({'dir': 'rr', 'key': sw, 'value' : 'straight'})
                else:
                    self._queue.put({'dir': 'rr', 'key': sw, 'value' : 'turnout'})

    def _onMessage(self, client, userdata, msg):

        if msg.topic == "rocrail/service/info":
            self._rocrailRx(msg.payload.decode('UTF-8'))

        elif msg.topic.startswith("rocrail_gw/command"):
            self._streamRx(msg.topic,msg.payload.decode('UTF-8'))

    def _run(self):

        client = None

        while self._runEnable:

            if client is None:

                print("Connecting to mqtt server")
                client = mqtt.Client("TrainSetMqttRelay")
                client.connect('172.16.20.1')
                client.on_message = self._onMessage
                client.subscribe("rocrail/service/info")
                client.subscribe("rocrail_gw/command/power")
                client.subscribe("rocrail_gw/command/stop")

                for k in self._switch:
                    client.subscribe(f"rocrail_gw/command/{k}")

                print("Connected to mqtt server")

            if self._queue.empty() is False:

                work = self._queue.get_nowait()

                if work['dir'] == 'sd':

                    if work['key'] == 'power':
                        client.publish(f"{self._name}/status/power", str(work['value']))

                    else:
                        client.publish(f"{self._name}/status/{work['key']}", str(work['value']))

                elif work['dir'] == 'rr':

                    if work['key'] == 'power':
                        if work['value'] == 'true':
                            client.publish(f"rocrail/service/client", '<sys cmd="go"/>')
                        else:
                            client.publish(f"rocrail/service/client", '<sys cmd="stop"/>')
                    else:
                        pl = '<sw id="' + work['key'] + '" cmd ="' + work['value'] + '" />'
                        client.publish(f"rocrail/service/client", pl.encode('UTF-8'))

            if client is not None:
                client.loop()

            time.sleep(.1)

ts = TrainSetInterface()

ts.start()

try:
    while True:
        time.sleep(0.5)
except KeyboardInterrupt:
    print("Got cntrl-c, exiting")

ts.stop()


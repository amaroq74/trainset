#!/usr/bin/env python

import paho.mqtt.client as mqtt
import queue
import time
import threading
import xml.etree.ElementTree as etree

class TrainSetInterface(object):

    def __init__(self):

        self._toRrQueue = queue.SimpleQueue()
        self._fromRrQueue = queue.SimpleQueue()
        self._thread = threading.Thread(target=self._run)
        self._runEnable = False
        self._name = 'rocrail_gw'
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
        self._loco = {'CalTrain 914' : {'dir' : 'true', 'speed' : 0},
                      'SLRG 115' : {'dir' : 'true', 'speed' : 0}}

    def start(self):
        self._runEnable = True
        self._thread.start()

    def stop(self):
        self._runEnable = False
        self._thread.join()

    # Receive messages from rocrail server
    def _rocrailRx(self, payload):
        tree = etree.fromstring(payload)

        if tree.tag == 'state':
            power = tree.get('power') == 'true'
            self._fromRrQueue.put({'type': 'power', 'value' : power})

        elif tree.tag == 'sw' and tree.get('state') is not None:
            sid = tree.get('id')
            sstate = 'Thrown' if tree.get('state') == 'turnout'  else 'Closed'

            if sid in self._switch:
                self._switch[sid] = sstate

            self._fromRrQueue.put({'type': 'switch', 'key': sid, 'value' : sstate})

        elif tree.tag == 'lc':
            lid = tree.get('id')
            ldir = 'Forward' if tree.get('dir') == 'true' else 'Reverse'
            lv = tree.get('V')

            if lid in self._loco:
                self._loco[lid] = {'dir' : ldir, 'speed' : lv}

            self._fromRrQueue.put({'type': 'loco', 'key' : lid, 'sub' : 'dir', 'value' : ldir})
            self._fromRrQueue.put({'type': 'loco', 'key' : lid, 'sub' : 'speed', 'value' : lv})

        else:
            #print(f"Other message: {payload}")
            pass

    def _streamRx(self, topic, payload):

        if topic == "rocrail_gw/command/power/power":
            if payload == "True":
                self._toRrQueue.put({'type': 'power', 'key': 'power', 'value' : 'true'})
            else:
                self._toRrQueue.put({'type': 'power', 'key': 'power', 'value' : 'false'})

        elif topic == "rocrail_gw/command/power/stop":
            self._toRrQueue.put({'type': 'power', 'key': 'stop', 'value' : 'true'})

        elif topic.startswith("rocrail_gw/command/switch/"):
            sw = topic.split('/')[3]

            if sw in self._switch:
                if self._switch[sw] == 'Thrown':
                    self._toRrQueue.put({'type': 'switch', 'key': sw, 'value' : 'straight'})
                else:
                    self._toRrQueue.put({'type': 'switch', 'key': sw, 'value' : 'turnout'})

        elif topic.startswith("rocrail_gw/command/loco/"):
            loco = topic.split('/')[3]
            sub = topic.split('/')[4]

            if loco in self._loco:

                if sub == 'dir':
                    if self._loco[loco]['dir'] == 'Forward':
                        self._toRrQueue.put({'type': 'loco', 'key': loco, 'sub' : 'dir', 'value' : 'false'})
                    else:
                        self._toRrQueue.put({'type': 'loco', 'key': loco, 'sub' : 'dir', 'value' : 'true'})

                elif sub == 'speed':
                    if payload == 'Stop':
                        newSpd = 0
                    elif payload == 'Up':
                        newSpd = int(self._loco[loco]['speed']) + 5
                    else:
                        newSpd = int(self._loco[loco]['speed']) - 5

                    if newSpd < 0:
                        newSpd = 0
                    elif newSpd > 100:
                        newSpd = 100

                    self._toRrQueue.put({'type': 'loco', 'key': loco, 'sub' : 'speed', 'value' : str(newSpd)})

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
                client.subscribe("rocrail_gw/command/power/power")
                client.subscribe("rocrail_gw/command/power/stop")

                for k in self._switch:
                    client.subscribe(f"rocrail_gw/command/switch/{k}")

                for k in self._loco:
                    client.subscribe(f"rocrail_gw/command/loco/{k}/dir")
                    client.subscribe(f"rocrail_gw/command/loco/{k}/speed")

                print("Connected to mqtt server")

            # Process From Rocrail Message
            if self._fromRrQueue.empty() is False:
                work = self._fromRrQueue.get_nowait()

                if work['type'] == 'power':
                    client.publish(f"{self._name}/status/power", str(work['value']))

                elif work['type'] == 'switch':
                    client.publish(f"{self._name}/status/switch/{work['key']}", str(work['value']))

                elif work['type'] == 'loco':
                    client.publish(f"{self._name}/status/loco/{work['key']}/{work['sub']}", str(work['value']))

            # Process From streamdeck Message
            if self._toRrQueue.empty() is False:
                work = self._toRrQueue.get_nowait()

                if work['type'] == 'power' and work['key'] == 'power':
                    if work['value'] == 'true':
                        client.publish("rocrail/service/client", '<sys cmd="go"/>')
                    else:
                        client.publish("rocrail/service/client", '<sys cmd="stop"/>')

                elif work['type'] == 'power' and work['key'] == 'stop':
                    client.publish("rocrail/service/client", '<sys cmd="ebreak"/>')

                elif work['type'] == 'switch':
                    pl = '<sw id="' + work['key'] + '" cmd ="' + work['value'] + '" />'
                    client.publish("rocrail/service/client", pl)

                elif work['type'] == 'loco':
                    if work['sub'] == 'dir':
                        pl = '<lc id="' + work['key'] + '" dir ="' + work['value'] + '" />'
                        client.publish("rocrail/service/client", pl)
                    elif work['sub'] == 'speed':
                        pl = '<lc id="' + work['key'] + '" V ="' + work['value'] + '" />'
                        client.publish("rocrail/service/client", pl)

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

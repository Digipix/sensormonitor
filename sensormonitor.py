#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2013 Roger Light <roger@atchoo.org>
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Eclipse Distribution License v1.0
# which accompanies this distribution.
#
# The Eclipse Distribution License is available at
#   http://www.eclipse.org/org/documents/edl-v10.php.
#
# Contributors:
#    Roger Light - initial implementation
#    Sverre Stendal - adding SensorCheck class and modifications in April 2018
#
# This code will monitor a sensor value over MQTT and send a warning message via HTTP POST if the sensor value
# has been too high for more than 5 minutes.
# After a warning is sent, the sensor value must be under the threshold for 5 minutes, before a new warning can be sent.


import json
import requests
import paho.mqtt.client as mqtt


# Most of this class is copied from https://github.com/eclipse/paho.mqtt.python/blob/master/examples/client_sub-class.py
class MyMQTTClass(mqtt.Client):

    def on_connect(self, mqttc, obj, flags, rc):
        print("rc: "+str(rc))

    def on_message(self, mqttc, obj, msg):
        # here we need to add some error handling (try / except)
        print(msg.topic+" "+str(msg.qos)+" "+str(msg.payload))
        message = str(msg.payload.decode("utf-8", "ignore"))
        decoded_json_message = json.loads(message)

        # current timestamp and sensorvalue
        sensorvalue = decoded_json_message["value"]
        timestamp = decoded_json_message["timestamp"]
        sensorchk.update(sensorvalue, timestamp)

    def on_publish(self, mqttc, obj, mid):
        print("mid: "+str(mid))

    def on_subscribe(self, mqttc, obj, mid, granted_qos):
        print("Subscribed: "+str(mid)+" "+str(granted_qos))

    def on_log(self, mqttc, obj, level, string):
        print(string)

    def run(self):
        self.connect("test.mosquitto.org")
        self.subscribe("sensors/lyse-test-01")

        rc = 0
        while rc == 0:
            rc = self.loop()
        return rc


# This is my own code!
# inspiration from http://www.steves-internet-guide.com/python-mqtt-publish-subscribe/
# and https://stackoverflow.com/questions/42473168/send-http-post-with-python
# and https://pythonspot.com/json-encoding-and-decoding-with-python/
# and https://github.com/bonus85/mqtt-xml
class SensorCheck:

    def __init__(self, warning_url, threshold):
        self.warning_url = warning_url
        self.threshold = threshold
        self.below_threshold_counter = 0
        self.above_threshold_counter = 0
        self.warning_sent = False

    def update(self, sensorvalue, timestamp):

        # We must wait 5 minutes before we can send a warning
        # times_to_wait = 30  # 6 times per minute * 5 minutes
        times_to_wait = 30

        if sensorvalue < threshold:  # below threshold

            # first we reset the over_threshold_counter
            self.above_threshold_counter = 0
            print("Value is below threshold")

            # start counting how many times we are below threshold
            self.below_threshold_counter = self.below_threshold_counter + 1
            print("below_threshold_counter =", self.below_threshold_counter)

            # if we have waited 5 minutes below threshold, we can allow a new warning to be sent
            if self.below_threshold_counter > times_to_wait:
                self.warning_sent = False
                print("warning ready to send", self.warning_sent)

        else:  # above threshold

            # first we reset the under_threshold_counter
            self.below_threshold_counter = 0
            print("Value is above threshold")

            # start counting how many times we are above threshold
            self.above_threshold_counter = self.above_threshold_counter + 1
            print("above_threshold_counter =", self.above_threshold_counter)

            # if we have waited 5 minutes above threshold, we can send one warning message
            if self.above_threshold_counter > times_to_wait:
                # first we check if a recent warning was sent
                if self.warning_sent :
                    print("warning already sent")
                else:
                    # SENDING THE WARNING HERE
                    print("Send warning")
                    data = dict()
                    data["message"] = "threshold value exceeded"
                    data["lastSensorTimestamp"] = timestamp
                    data["lastSensorValue"] = sensorvalue
                    # here we need to add some error handling (try / except)
                    response = requests.post(warning_url, data=data)
                    print("Response from server: ", response.text)
                    self.warning_sent = True


if __name__ == '__main__':

    # The config file contains the url to the server that will receive the warning
    # and the threshold value that will trigger the warning

    with open('config.json') as f:  # inspiration from https://github.com/bonus85/mqtt-xml
        config = json.load(f)
        warning_url = config['warning_server']
        threshold = config['threshold_value']

    sensorchk = SensorCheck(warning_url, threshold)
    mqttc = MyMQTTClass()
    rc = mqttc.run()
    print("rc: "+str(rc))

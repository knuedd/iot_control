#!/usr/bin/python3
# -*- coding: utf-8 -*-

""" backend for mqtt and Home Assistant
"""


import json
from typing import Dict
import logging
import socket
from iot_control.iotbackendbase import IoTBackendBase
from iot_control.iotdevicebase import IoTDeviceBase
from iot_control.iotfactory import IoTFactory

import paho.mqtt.client as mqtt


@IoTFactory.register_backend("mqtt_hass")
class BackendMqttHass(IoTBackendBase):
    """ the backend class for mqtt and Home Assistant

    Args:
        IoTBackendBase: the base class
    """
    avail_topics = []
    state_topics = {}
    command_topics = {}
    devices = []

    def __init__(self, **kwargs):
        super().__init__()
        self.logger = logging.getLogger("iot_control")
        config = kwargs.get("config", None)
        self.config = config
        self.mqtt_client = mqtt.Client(client_id="iot_control"+str(socket.gethostname()))
        self.mqtt_client.on_connect = self.mqtt_callback_connect
        self.mqtt_client.on_message = self.mqtt_callback_message
        self.mqtt_client.on_disconnect = self.mqtt_callback_disconnect
        self.logger.info("connection to mqtt server")

        if config['user'] and config['password']:
            self.mqtt_client.username_pw_set(
                username=config['user'], password=config['password'])

        self.mqtt_client.connect(
            self.config['server'], self.config['port'], 60)
        self.mqtt_client.loop_start()


    def register_device(self, device: IoTDeviceBase) -> None:
        self.devices.append(device)

    def shutdown(self):
        self.logger.info("shutdown mqtt connection")
        for avail_topic in self.avail_topics:
            self.mqtt_client.publish(avail_topic, self.config["offline_payload"], retain=True)
        self.mqtt_client.disconnect()
        self.mqtt_client.loop_stop()

    def workon(self, device: IoTDeviceBase, data: Dict):

        if not device in self.state_topics:
            self.logger.error("unknown device")
            return

        state_topics = self.state_topics[device]

        if "sensors" in device.conf:
            for entry in data:
                if entry in state_topics:
                    val = {entry: data[entry]}
                    state_topic = state_topics[entry]
                    self.logger.debug("new mqtt value for %s : %s", state_topic, val)
                    self.mqtt_client.publish(state_topic, json.dumps(val), retain=True)

        elif "switches" in device.conf:
            for entry in data:
                if entry in state_topics:
                    val = data[entry]
                    state_topic = state_topics[entry]
                    self.logger.debug("new mqtt value for %s : %s", state_topic, val)
                    self.mqtt_client.publish(state_topic, val, retain=True)

        elif "binary-sensors" in device.conf:
            for entry in data:
                if entry in state_topics:
                    val = data[entry]
                    state_topic = state_topics[entry]
                    self.logger.debug("new mqtt value for %s : %s", state_topic, val)
                    self.mqtt_client.publish(state_topic, val, retain=True)

        elif "covers" in device.conf:
            for entry in data:
                if entry in state_topics:
                    val = data[entry]
                    state_topic = state_topics[entry]
                    self.logger.debug("new mqtt value for %s : %s", state_topic, val)
                    self.mqtt_client.publish(state_topic, val, retain=True)

        elif "poscovers" in device.conf:
            for entry in data:
                if entry in state_topics:
                    #val = data[entry]
                    val = {entry: data[entry]}
                    state_topic = state_topics[entry]
                    self.logger.debug("new mqtt value for %s : %s", state_topic, val)
                    #self.mqtt_client.publish(state_topic, val, retain=True)
                    self.mqtt_client.publish(state_topic, json.dumps(val), retain=True)

        else:
            self.logger.error("workon(): unknown device type %s", device.conf)


    def announce(self):

        for device in self.devices:

            state_topics = {}

            # is it a sensor or a switch
            if "sensors" in device.conf:
                # get list of sensors on device
                sensors = device.conf["sensors"]
                # create a state topic for everyone
                try:
                    sensor_cfg = device.conf["sensors"]
                    for sensor in sensors:
                        self.logger.info("mqtt announcing sensor %s", sensor)
                        try:
                            sconf = sensor_cfg[sensor]
                            config_topic = "{}/sensor/{}/{}/config".format(
                                self.config["hass_discovery_prefix"],
                                sconf["unique_id"], sensor)
                            state_topic = "{}/sensor/{}/state".format(
                                self.config["hass_discovery_prefix"],
                                sconf["unique_id"])
                            avail_topic = "{}/sensor/{}/avail".format(
                                self.config["hass_discovery_prefix"],
                                sconf["unique_id"])
                            self.avail_topics.append(avail_topic)
                            state_topics[sensor] = state_topic
                            conf_dict = {
                                "device_class": sconf["device_class"],
                                "name": sconf["name"],
                                "unique_id": sconf["unique_id"],
                                "state_topic": state_topic,
                                "availability_topic": avail_topic,
                                "unit_of_measurement": sconf["unit_of_measurement"],
                                "value_template": "{{ value_json." + sensor + " }}",
                                "expire_after": sconf["expire_after"],
                                "payload_available": self.config["online_payload"],
                                "payload_not_available": self.config["offline_payload"]
                            }
                            payload = json.dumps(conf_dict)
                            self.logger.info("publishing: %s", payload)
                            result = self.mqtt_client.publish(
                                config_topic, payload, retain=True)
                            result = self.mqtt_client.publish(
                                avail_topic, self.config["online_payload"], retain=True)
                        except Exception as exception:
                            self.logger.error("problem bringing sensor %s up: %s",
                                              sensor, exception)
                except Exception as exception:
                    self.logger.error(
                        "error announcing sensor: %s", exception)
            elif "switches" in device.conf:

                # get list of switches on device
                switches = device.sensor_list()
                # create a state topic for everyone
                try:
                    switches_cfg = device.conf["switches"]
                    for switch in switches:
                        try:
                            self.logger.info(
                                "mqtt announcing switch %s", switch)
                            sconf = switches_cfg[switch]
                            config_topic = "{}/switch/{}/{}/config".format(
                                self.config["hass_discovery_prefix"],
                                sconf["unique_id"], switch)
                            state_topic = "{}/switch/{}/state".format(
                                self.config["hass_discovery_prefix"],
                                sconf["unique_id"])
                            avail_topic = "{}/switch/{}/avail".format(
                                self.config["hass_discovery_prefix"],
                                sconf["unique_id"])
                            command_topic = "{}/switch/{}/command".format(
                                self.config["hass_discovery_prefix"],
                                sconf["unique_id"])
                            self.avail_topics.append(avail_topic)
                            state_topics[switch] = state_topic
                            conf_dict = {
                                "name": sconf["name"],
                                "unique_id": sconf["unique_id"],
                                "state_topic": state_topic,
                                "availability_topic": avail_topic,
                                "command_topic": command_topic,
                                "value_template": "{{ value_json." + switch + " }}",
                                "payload_available": self.config["online_payload"],
                                "payload_not_available": self.config["offline_payload"],
                                "payload_on": self.config["payload_on"],
                                "payload_off": self.config["payload_off"],
                                "state_on": self.config["payload_on"],
                                "state_off": self.config["payload_off"],
                                "optimistic": "false",
                                #"qos": 0,
                                #"retain": true
                            }
                            payload = json.dumps(conf_dict)

                            self.logger.info("publishing: %s", payload)
                            self.mqtt_client.publish(config_topic, payload, retain=True)
                            self.mqtt_client.publish(avail_topic,
                                                     self.config["online_payload"], retain=True)

                            # now subscribe to the command topic
                            (result, _) = self.mqtt_client.subscribe(
                                command_topic)
                            self.logger.info(
                                "subscription result: %s", result)
                            self.command_topics[command_topic] = [
                                device, switch, state_topic
                            ]
                        except Exception as exception:
                            self.logger.error("error announcing switch %s: %s",
                                              switch, exception)
                except Exception as exception:
                    self.logger.error(
                        "error while registering switch: %s", exception)

            elif "binary-sensors" in device.conf:

                # get list of sensors on device
                sensors = device.conf["binary-sensors"]
                # create a state topic for everyone
                try:
                    sensor_cfg = device.conf["binary-sensors"]
                    for sensor in sensors:
                        self.logger.info("mqtt announcing sensor %s", sensor)
                        try:
                            sconf = sensor_cfg[sensor]
                            config_topic = "{}/binary_sensor/{}/{}/config".format(
                                self.config["hass_discovery_prefix"],
                                sconf["unique_id"], sensor)
                            state_topic = "{}/binary_sensor/{}/state".format(
                                self.config["hass_discovery_prefix"],
                                sconf["unique_id"])
                            avail_topic = "{}/binary_sensor/{}/avail".format(
                                self.config["hass_discovery_prefix"],
                                sconf["unique_id"])
                            self.avail_topics.append(avail_topic)
                            state_topics[sensor] = state_topic
                            conf_dict = {
                                "device_class": sconf["device_class"],
                                "name": sconf["name"],
                                "unique_id": sconf["unique_id"],
                                "state_topic": state_topic,
                                "availability_topic": avail_topic,
                                "device_class": sconf["device_class"],
                                "payload_available": self.config["online_payload"],
                                "payload_not_available": self.config["offline_payload"]
                            }
                            payload = json.dumps(conf_dict)
                            self.logger.info("publishing: %s", payload)
                            result = self.mqtt_client.publish(
                                config_topic, payload, retain=True)
                            result = self.mqtt_client.publish(
                                avail_topic, self.config["online_payload"], retain=True)
                        except Exception as exception:
                            self.logger.error("problem bringing sensor %s up: %s",
                                              sensor, exception)
                except Exception as exception:
                    self.logger.error(
                        "error announcing sensor: %s", exception)

            elif "covers" in device.conf:
                # get list of covers on device
                covers = device.conf["covers"]
                # create a state topic for everyone
                try:
                    cover_cfg = device.conf["covers"]
                    for cover in covers:
                        self.logger.info("MQTT announcing cover %s", cover)
                        try:
                            sconf = cover_cfg[cover]
                            config_topic = "{}/cover/{}/{}/config".format(
                                self.config["hass_discovery_prefix"],
                                sconf["unique_id"], cover)
                            state_topic = "{}/cover/{}/state".format(
                                self.config["hass_discovery_prefix"],
                                sconf["unique_id"])
                            avail_topic = "{}/cover/{}/avail".format(
                                self.config["hass_discovery_prefix"],
                                sconf["unique_id"])
                            command_topic = "{}/cover/{}/command".format(
                                self.config["hass_discovery_prefix"],
                                sconf["unique_id"])
                            self.avail_topics.append(avail_topic)
                            state_topics[cover] = state_topic
                            conf_dict = {
                                "name": sconf["name"],
                                "unique_id": sconf["unique_id"],
                                "state_topic": state_topic,
                                "availability_topic": avail_topic,
                                "command_topic": command_topic,
                                "value_template": "{{ value_json." + cover + " }}",
                                "payload_available": self.config["online_payload"],
                                "payload_not_available": self.config["offline_payload"],
                                "state_open": self.config["state_open"],
                                "state_opening": self.config["state_opening"],
                                "state_closed": self.config["state_closed"],
                                "state_closing": self.config["state_closing"],
                                "payload_open": self.config["payload_open"],
                                "payload_close": self.config["payload_close"],
                                "payload_stop": self.config["payload_stop"],
                                "optimistic": "false"
                            }
                            payload = json.dumps(conf_dict)
                            self.logger.info("publishing: %s", payload)
                            result = self.mqtt_client.publish(
                                config_topic, payload, retain=True)
                            result = self.mqtt_client.publish(
                                avail_topic, self.config["online_payload"], retain=True)

                            # now subscribe to the command topic
                            (result, _) = self.mqtt_client.subscribe(
                                command_topic)
                            self.logger.info(
                                "subscription result: %s", result)
                            self.command_topics[command_topic] = [
                                device, cover, state_topic
                            ]

                        except Exception as exception:
                            self.logger.error("problem bringing cover %s up: %s",
                                              cover, exception)
                except Exception as exception:
                    self.logger.error(
                        "error announcing cover: %s", exception)

            elif "poscovers" in device.conf:

                # get list of covers on device
                covers = device.conf["poscovers"]
                # create a state topic for everyone
                try:
                    cover_cfg = device.conf["poscovers"]

                    for cover in covers:
                        self.logger.info("MQTT announcing positional cover %s", cover)
                        try:
                            sconf = cover_cfg[cover]

                            config_topic = "{}/cover/{}/{}/config".format(
                                self.config["hass_discovery_prefix"],
                                sconf["unique_id"], cover)
                            position_topic = "{}/cover/{}/position".format(
                                self.config["hass_discovery_prefix"],
                                sconf["unique_id"])
                            set_position_topic = "{}/cover/{}/set_position".format(
                                self.config["hass_discovery_prefix"],
                                sconf["unique_id"])
                            avail_topic = "{}/cover/{}/avail".format(
                                self.config["hass_discovery_prefix"],
                                sconf["unique_id"])
                            command_topic = "{}/cover/{}/command".format(
                                self.config["hass_discovery_prefix"],
                                sconf["unique_id"])
                            self.avail_topics.append(avail_topic)
                            state_topics[cover] = position_topic
                            conf_dict = {
                                "name": sconf["name"],
                                "unique_id": sconf["unique_id"],
                                "position_topic": position_topic,
                                "set_position_topic": set_position_topic,
                                "availability_topic": avail_topic,
                                "command_topic": command_topic,
                                "value_template": "{{ value_json." + cover + " }}",
                                "payload_available": self.config["online_payload"],
                                "payload_not_available": self.config["offline_payload"],
                                "position_open": 100,
                                "position_closed": 0,
                                "payload_open": sconf["payload_open"],
                                "payload_close": sconf["payload_close"],
                                "payload_stop": sconf["payload_stop"],
                                "optimistic": "false"
                            }
                            payload = json.dumps(conf_dict)
                            self.logger.info("publishing: %s", payload)
                            result = self.mqtt_client.publish(
                                config_topic, payload, retain=True)
                            result = self.mqtt_client.publish(
                                avail_topic, self.config["online_payload"], retain=True)

                            # now subscribe to the command topic
                            (result, _) = self.mqtt_client.subscribe(command_topic)
                            self.logger.info("subscription result: %s", result)
                            self.command_topics[command_topic] = [device, cover, position_topic]

                            # now subscribe to the set_position topic
                            (result, _) = self.mqtt_client.subscribe(set_position_topic)
                            self.logger.info("subscription result: %s", result)
                            self.command_topics[set_position_topic] = [device, cover, position_topic]

                        except Exception as exception:
                            self.logger.error("problem bringing poscover %s up: %s",
                                              cover, exception)
                except Exception as exception:
                    self.logger.error(
                        "error announcing poscover: %s", exception)

            else:
                self.logger.error("announce(): unknown device type %s", device.conf)

            # finally add device's state topics list to permanent list
            self.state_topics[device] = state_topics

    # The callback for when the client receives a CONNACK response from the server.

    def mqtt_callback_connect(self, client, userdata, flags, rc):
        """ callback as defined by the mqtt API for the moment
            when the connection is made
        """
        (result, _) = self.mqtt_client.subscribe("homeassistant/status")
        self.logger.info(
            "subscription result for homeassistant/status: %s", result)
        self.announce()

    # The callback for when a PUBLISH message is received from the server.
    def mqtt_callback_message(self, client, userdata, msg):
        """ callback from mqtt in case message arrives
        """

        if msg.topic in self.command_topics:
            payload = msg.payload.decode("utf-8")
            [device, switch, state_topic] = self.command_topics[msg.topic]
            self.logger.debug("calling device %s, switch %s with %s",
                              device, switch, payload)
            if device.set_state({switch: payload}):
                self.mqtt_client.publish(state_topic, payload)

        if msg.topic == "homeassistant/status":
            if msg.payload == b'online':
                self.logger.info("Home Assistant came online")
                # no need to re-announce myself to home assistant here because the retained 
                # announcement messages will take care of this in a much nicer way
            elif msg.payload == b'offline':
                self.logger.info("Home Assistant went offline")
            else:
                self.logger.info("unexpected home assistant status "
                                 "message: %s %s", msg.topic, msg.payload)

    def mqtt_callback_disconnect(self, client, userdata, rc):
        """ mqtt callback when the client gets disconnected
        """
        if rc != 0:
            self.logger.warning("Unexpected disconnection.")

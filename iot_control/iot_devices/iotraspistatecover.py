#!/usr/bin/python
# -*- coding: utf-8 -*-

""" Raspi state cover device
"""
import time
import logging
from typing import Dict
import RPi.GPIO as GPIO
from iot_control.iotdevicebase import IoTDeviceBase
from iot_control.iotfactory import IoTFactory


@IoTFactory.register_device("raspi-state-cover")
class IoTraspicover(IoTDeviceBase):
    """ Cover pr garage door with two input GPIO pins for detecting the
    closed and open states and one output GPIO pin triggering the motor
    controller
    """

    logger = None

    # constants for the internal state, they get translated into what HA/MQTT understand
    STATE_OPEN = 1
    STATE_OPENING = 2
    STATE_CLOSED = 3
    STATE_CLOSING = 4
    STATE_STOPPED_OPENING = 5
    STATE_STOPPED_CLOSING = 6
    STATE_UNKNOWN = 7
    STATE_ILLEGAL = 8

    # translate above constants into the proper values as cover config says
    # and as HA/MQTT understand
    translate_status = {}

    state_open = "open"
    state_opening = "opening"
    state_closed = "closed"
    state_closing = "closing"
    state_unknown = "unknown"

    # stores mapping of covers to pins
    covers = {}

    # handle for a pending autooff event
    handle = None

    def __callback(self, pin, cfg):
        """ The real callback function acting upon a state change of one of the GPIO pins """

        pin_up = cfg["pin_up"]
        pin_down = cfg["pin_down"]

        state_pin_up = not GPIO.input(pin_up)
        state_pin_down = not GPIO.input(pin_down)

        if state_pin_up and state_pin_down:
            self.logger.error("IoTraspicover.__callback(): both input pins "
                              "true --> illegal state")
            cfg["status"] = IoTraspicover.STATE_ILLEGAL
            return

        if pin == pin_up:

            # upper pin changed
            if state_pin_up:
                # upper pin changed from open to closed, so the cover is open
                cfg["status"] = IoTraspicover.STATE_OPEN #self.conf["state_open"]
            else:
                # lower pin changed from closed to open, so the cover is opening
                cfg["status"] = IoTraspicover.STATE_CLOSING #self.conf["state_closing"]

        elif pin == pin_down:

            # lower pin changed
            if state_pin_down:
                # lower pin changed from open to closed, so the cover is closed now
                cfg["status"] = IoTraspicover.STATE_CLOSED #self.conf["state_closed"]
            else:
                # lower pin changed from closed to open, so the cover is opening
                cfg["status"] = IoTraspicover.STATE_OPENING #self.conf["state_opening"]

        else:
            self.logger.error("IoTraspicover.__callback(): "
                              "unknown pin %d, something is wrong", pin)

        self.runtime.trigger_for_device(self)

    def __init__(self, **kwargs):
        super().__init__()
        setupdata = kwargs.get("config")
        self.logger = logging.getLogger("iot_control")

        self.conf = setupdata
        GPIO.setmode(GPIO.BCM)  # GPIO Nummern statt Board Nummern
        GPIO.setwarnings(False)

        if "state_open" in self.conf:
            self.state_open = self.conf["state_open"]
        if "state_opening" in self.conf:
            self.state_opening = self.conf["state_opening"]
        if "state_closed" in self.conf:
            self.state_closed = self.conf["state_closed"]
        if "state_closing" in self.conf:
            self.state_closing = self.conf["state_closing"]
        if "state_unknown" in self.conf:
            self.state_unknown = self.conf["state_unknown"]

        self.translate_status[IoTraspicover.STATE_OPEN] = self.state_open
        self.translate_status[IoTraspicover.STATE_OPENING] = self.state_opening
        self.translate_status[IoTraspicover.STATE_CLOSED] = self.state_closed
        self.translate_status[IoTraspicover.STATE_CLOSING] = self.state_closing
        self.translate_status[IoTraspicover.STATE_STOPPED_OPENING] = self.state_unknown
        self.translate_status[IoTraspicover.STATE_STOPPED_CLOSING] = self.state_unknown
        self.translate_status[IoTraspicover.STATE_UNKNOWN] = self.state_unknown
        self.translate_status[IoTraspicover.STATE_ILLEGAL] = self.state_unknown

        covers_cfg = setupdata["statecovers"]

        

        def callback(pin):
            """ Helper callback function providing all the interesting
            arguments that the stupid API of GPIO.add_event_detect() doesn't
            like to give us"""
            self.logger.debug("IoTraspicover: GPIO callback on pin %d", pin)
            for cover in covers_cfg:
                if pin == covers_cfg[cover]["pin_up"] or pin == covers_cfg[cover]["pin_down"]:

                    self.__callback(pin, covers_cfg[cover])

        for cover in covers_cfg:
            cfg = covers_cfg[cover]
            pin_up = cfg["pin_up"]
            pin_down = cfg["pin_down"]
            pin_trigger = cfg["pin_trigger"]

            cfg["status"] = IoTraspicover.STATE_UNKNOWN
            GPIO.setup(pin_up, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(pin_down, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(pin_trigger, GPIO.OUT, initial=GPIO.HIGH)

            state_pin_up = not GPIO.input(pin_up)
            state_pin_down = not GPIO.input(pin_down)

            if not state_pin_up and not state_pin_down:
                cfg["status"] = IoTraspicover.STATE_UNKNOWN
            elif state_pin_up and not state_pin_down:
                cfg["status"] = IoTraspicover.STATE_OPEN
            elif not state_pin_up and state_pin_down:
                cfg["status"] = IoTraspicover.STATE_CLOSED
            else:
                self.logger.error("IoTraspicover.__init()__: "
                                  "both input pins true --> illegal state")
                cfg["status"] = IoTraspicover.STATE_ILLEGAL

            self.logger.info("new IoTraspicover device with input pins %d, %d "
                             "and output pin %d, initial state %s ",
                             pin_down, pin_up, pin_trigger,
                             self.translate_status[cfg["status"]])

            self.covers[cover] = cfg

            GPIO.add_event_detect(pin_up, GPIO.BOTH, callback=callback,
                                  bouncetime=100)
            GPIO.add_event_detect(pin_down, GPIO.BOTH, callback=callback,
                                  bouncetime=100)

    def read_data(self) -> Dict:
        """ don't read real data or gpios but just return the stored status  """
        val = {}
        for cover in self.covers:
            val[cover] = self.translate_status[self.covers[cover]["status"]]
        return val

    def sensor_list(self) -> list:
        return self.covers.keys()

    def __trigger_pin_once(self, cfg):

        self.logger.debug("trigger once pin %i: %i -> %i -> %i", 
                             cfg["pin_trigger"], GPIO.input(cfg["pin_trigger"]), GPIO.LOW, GPIO.HIGH )

        GPIO.output(cfg["pin_trigger"], GPIO.LOW)
        time.sleep(0.1)
        GPIO.output(cfg["pin_trigger"], GPIO.HIGH)

    def __trigger_pin_twice(self, cfg):

        self.logger.debug("trigger twice pin %i: %i -> %i -> %i pause -> %i -> %i", 
                             cfg["pin_trigger"], GPIO.input(cfg["pin_trigger"]), GPIO.LOW, GPIO.HIGH, GPIO.LOW, GPIO.HIGH )

        GPIO.output(cfg["pin_trigger"], GPIO.LOW)
        time.sleep(0.1)
        GPIO.output(cfg["pin_trigger"], GPIO.HIGH)

        time.sleep(1.0)

        GPIO.output(cfg["pin_trigger"], GPIO.LOW)
        time.sleep(0.1)
        GPIO.output(cfg["pin_trigger"], GPIO.HIGH)

    def set_state(self, messages: Dict) -> bool:
        """ Commands from Home Assistant MQTT arrive here """
        self.logger.debug("IoTraspicover.setstate() %s", messages)

        for cover in self.covers:
            if cover in messages:
                msg = messages[cover]
                oldstate = self.covers[cover]["status"]

                if msg == self.conf["payload_open"]:

                    if IoTraspicover.STATE_OPEN == oldstate:
                        pass
                    elif IoTraspicover.STATE_OPENING == oldstate:
                        pass
                    elif IoTraspicover.STATE_CLOSED == oldstate:
                        self.__trigger_pin_once(self.covers[cover])
                    elif IoTraspicover.STATE_CLOSING == oldstate:
                        self.__trigger_pin_twice(self.covers[cover])
                        self.covers[cover]["status"] = IoTraspicover.STATE_OPENING
                    elif IoTraspicover.STATE_STOPPED_OPENING == oldstate:
                        self.__trigger_pin_twice(self.covers[cover])
                        self.covers[cover]["status"] = IoTraspicover.STATE_OPENING
                    elif IoTraspicover.STATE_STOPPED_CLOSING == oldstate:
                        self.__trigger_pin_once(self.covers[cover])
                        self.covers[cover]["status"] = IoTraspicover.STATE_OPENING
                    elif IoTraspicover.STATE_UNKNOWN == oldstate:
                        self.__trigger_pin_once(self.covers[cover])
                    else:
                        self.logger.error("IoTraspicover.set_state(): unknown "
                                          "previous state %s", oldstate)

                elif msg == self.conf["payload_close"]:

                    if IoTraspicover.STATE_OPEN == oldstate:
                        self.__trigger_pin_once(self.covers[cover])
                    elif IoTraspicover.STATE_OPENING == oldstate:
                        self.__trigger_pin_twice(self.covers[cover])
                        self.covers[cover]["status"] = IoTraspicover.STATE_CLOSING
                    elif IoTraspicover.STATE_CLOSED == oldstate:
                        pass
                    elif IoTraspicover.STATE_CLOSING == oldstate:
                        pass
                    elif IoTraspicover.STATE_STOPPED_OPENING == oldstate:
                        self.__trigger_pin_once(self.covers[cover])
                        self.covers[cover]["status"] = IoTraspicover.STATE_CLOSING
                    elif IoTraspicover.STATE_STOPPED_CLOSING == oldstate:
                        self.__trigger_pin_twice(self.covers[cover])
                        self.covers[cover]["status"] = IoTraspicover.STATE_CLOSING
                    elif IoTraspicover.STATE_UNKNOWN == oldstate:
                        self.__trigger_pin_once(self.covers[cover])
                    else:
                        self.logger.error("IoTraspicover.set_state(): unknown "
                                          "previous state %s", oldstate)

                elif msg == self.conf["payload_stop"]:

                    if IoTraspicover.STATE_OPEN == oldstate:
                        pass
                    elif IoTraspicover.STATE_OPENING == oldstate:
                        self.__trigger_pin_once(self.covers[cover])
                        self.covers[cover]["status"] = IoTraspicover.STATE_STOPPED_OPENING
                    elif IoTraspicover.STATE_CLOSED == oldstate:
                        pass
                    elif IoTraspicover.STATE_CLOSING == oldstate:
                        self.__trigger_pin_once(self.covers[cover])
                        self.covers[cover]["status"] = IoTraspicover.STATE_STOPPED_CLOSING
                    elif IoTraspicover.STATE_STOPPED_OPENING == oldstate:
                        pass
                    elif IoTraspicover.STATE_STOPPED_CLOSING == oldstate:
                        pass
                    elif IoTraspicover.STATE_UNKNOWN == oldstate:
                        pass
                    else:
                        self.logger.error("IoTraspicover.set_state(): unknown "
                                          "previous state %s", oldstate)

                else:
                    self.logger.error("IoTraspicover.set_state(): "
                                      "unknown command %s", msg)

        # return False so that the mqtthass will _not_ publish the updated
        # state right away
        return False

    def shutdown(self, _) -> None:
        for cover in self.covers:
            cfg = self.covers[cover]
            pin_trigger = cfg["pin_trigger"]
            #GPIO.output(pin_trigger, GPIO.HIGH)

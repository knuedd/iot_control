#!/usr/bin/python
# -*- coding: utf-8 -*-

""" definitions for GPIO pins on a raspberry pi
"""

from typing import Dict
import RPi.GPIO as GPIO
import logging
from iot_control.iotdevicebase import IoTDeviceBase
from iot_control.iotfactory import IoTFactory


@IoTFactory.register_device("raspi-gpio")
class IoTraspigpio(IoTDeviceBase):
    """ Raspberry pi GPIO class
    """

    # stores mapping of switches to pins
    switches = {}
    autooff = {}
    value_on = {}
    value_off = {}
    handle = {} # handle for a pending autooff event

    def __init__(self, **kwargs):
        super().__init__()
        setupdata = kwargs.get("config")
        self.conf = setupdata
        GPIO.setmode(GPIO.BCM)  # GPIO Nummern statt Board Nummern
        GPIO.setwarnings(False)

        # transition code: make sure the old version with 'names' instead of 
        # 'switches' in setup.yaml is also accepted TODO: delete some time in the future
        if "names" in setupdata:
            logger = logging.getLogger("iot_control")
            logger.info("PLEASE UPDATE: Your setup.yaml uses 'names' instead of 'switches' in the raspi-gpio section.")
            setupdata["switches"]= setupdata["names"]

        switches_cfg = setupdata["switches"]
        for switch in switches_cfg:
            cfg = switches_cfg[switch]
            pin = cfg["pin"]
            if "autooff" in cfg:
                self.autooff[switch] = cfg["autooff"]
            self.value_on[switch]= GPIO.HIGH
            self.value_off[switch]= GPIO.LOW

            #print("default: on == HIGH and off == LOW" )
            if "inverse" in cfg and cfg["inverse"] > 0 :
                self.value_on[switch]= GPIO.LOW
                self.value_off[switch]= GPIO.HIGH
                #print("inverse: on == LOW and off == HIGH" )
            GPIO.setup(pin, GPIO.OUT, initial=self.value_off[switch])  # GPIO Modus zuweisen
            self.switches[switch] = pin

    def give_scheduled_event_handle(self,handle,msg) -> None: # TODO
        self.handle[msg]= handle
  
    def read_data(self) -> Dict:
        """ read data """
        val = {}
        for switch in self.switches:
            pin = self.switches[switch]
            if self.value_off[switch] == GPIO.input(pin):
                payload = self.conf["payload_off"]
            else:
                payload = self.conf["payload_on"]
            val[switch] = payload
        return val

    def sensor_list(self) -> list:
        return self.switches.keys()

    def set_state(self, messages: Dict) -> bool:
        for msg in messages:
            if msg in self.switches:
                pin = self.switches[msg]
                if messages[msg] == self.conf["payload_on"]:
                    GPIO.output(pin, self.value_on[msg])
                    if msg in self.autooff:
                        self.runtime.schedule_for_device(
                            self.autooff[msg], self, msg, self.conf["payload_off"])
                elif messages[msg] == self.conf["payload_off"]:
                    GPIO.output(pin, self.value_off[msg])
                    if msg in self.autooff and msg in self.handle:
                        if None != self.handle[msg]:
                            self.handle[msg].cancel()
                            self.handle[msg]= None
                else:
                    # unknown event
                    pass
                    
        return True

    def shutdown(self, _) -> None:
        """ Make sure to switch off the GPIO pin """
        for switch in self.switches:
            pin = self.switches[switch]
            GPIO.output(pin, GPIO.LOW)

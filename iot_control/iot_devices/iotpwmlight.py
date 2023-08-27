#!/usr/bin/python
# -*- coding: utf-8 -*-

""" Raspi PWM light for lights controlled through pulse width modulation 
between 0% and 100% according to https://www.home-assistant.io/integrations/light.mqtt/#brightness-and-no-rgb-support
"""

import time
import logging
from typing import Dict
import RPi.GPIO as GPIO
from iot_control.iotdevicebase import IoTDeviceBase
from iot_control.iotfactory import IoTFactory
import json

@IoTFactory.register_device("raspi-pwm-light")
class IoTraspipwmlight(IoTDeviceBase):
    """ LED light strip or light controlled by motor controller with PWM to adjust brightness
    """

    logger = None

    # stores mapping of covers to pins
    pwmlights= {}

    # handle for a pending autooff event
    handle = None

    def __init__(self, **kwargs):
        super().__init__()

        setupdata = kwargs.get("config")
        self.logger = logging.getLogger("iot_control")
        self.logger.debug("IoTraspipwmlight.__init__()")
        self.conf= setupdata

        # setup

        GPIO.setmode(GPIO.BCM)  # GPIO numbering instead of board numbers
        GPIO.setwarnings(False)

        pwmlight_cfg= setupdata["pwmlights"]
        for light in pwmlight_cfg:

            cfg= pwmlight_cfg[light]

            for pin in cfg['pins']:
                GPIO.setup(pin,GPIO.OUT)
                GPIO.output(pin,GPIO.LOW)

            GPIO.setup(cfg["pwmpin"],GPIO.OUT)
            cfg['pwm']= GPIO.PWM(cfg['pwmpin'],1000)
            cfg['pwm'].start(0)

            cfg['brightness']= 0 # 0-255 as used by HA, initially 0

            self.pwmlights[light]= cfg

    def read_data(self) -> Dict:

        val = {}
        for light in self.pwmlights:
            val[light] = self.pwmlights[light]['brightness']

        return val


    def sensor_list(self) -> list:
        return []

    def set_state(self, messages: Dict) -> bool:
        """ Commands from Home Assistant MQTT arrive here """
        self.logger.debug("IoTraspipwmlight.setstate() %s", messages)

        for light in self.pwmlights:
            if light in messages:

                cfg= self.pwmlights[light]

                # determine new brightness settings

                msg= messages[light]
                if msg.isdigit():

                    #print(" set light to ", int(msg))
                    cfg['brightness']= int(msg)

                elif msg == "ON":

                    #print(" set light to ", msg)

                    if cfg['brightness'] > 0:
                        #print("already ON")
                        pass
                    else:
                        #print("switching ON")
                        cfg['brightness']= 255

                elif msg == "OFF":

                    #print(" set light to ", msg)
                    cfg['brightness']= 0

                # apply new brightness settings

                if 0 == cfg['brightness']:

                    # switch off entirely, not just the PWM to zero

                    cfg['pwm'].ChangeDutyCycle(0)

                    # power pins off
                    for pin in cfg["pins"]:
                        GPIO.output(pin,GPIO.LOW)

                else:

                    # switch to appropriate PWM duty cycle
                    # duty cycle needs to be between 0 and 100
                    # brightness value as given by HA is 0 to 255

                    pwm_duty_cycle= int( cfg['brightness']*100.0/255.0 )
                    cfg['pwm'].ChangeDutyCycle(pwm_duty_cycle)
                    time.sleep(0.5)

                    # switch first pin to LOW and second pin to HIGH
                    GPIO.output(cfg['pins'][0],GPIO.LOW)
                    GPIO.output(cfg['pins'][1],GPIO.HIGH)

        return False


    def shutdown(self, _) -> None:

        for light in self.pwmlights:
            cfg= self.pwmlights[light]
            # PWM pin off
            cfg['pwm'].ChangeDutyCycle(0)
            # power pins off
            for pin in cfg["pins"]:
                GPIO.output(pin,GPIO.LOW)


        # must not GPIO cleanup here because other devices might still want to reset things
        #GPIO.cleanup()

#!/usr/bin/python
# -*- coding: utf-8 -*-

""" Raspi PWM light for lights controlled through pulse width modulation 
between 0% and 100% according to https://www.home-assistant.io/integrations/light.mqtt/#brightness-and-no-rgb-support
TODO work in progess
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
        print("IoTraspipwmlight.__init__()")
        print(setupdata)

        self.conf= setupdata

        # setup

        GPIO.setmode(GPIO.BCM)  # GPIO Nummern statt Board Nummern
        GPIO.setwarnings(False)



        pwmlight_cfg= setupdata["pwmlights"]
        for light in pwmlight_cfg:

            cfg= pwmlight_cfg[light]

            print("    cfg ", cfg )
            for pin in cfg['pins']:
                print("GPIO.setup({},GPIO.OUT)".format(pin))
                GPIO.setup(pin,GPIO.OUT)
                print("GPIO.output({},GPIO.LOW)".format(pin))
                GPIO.output(pin,GPIO.LOW)

            print("    pwm ", cfg['pwmpin'] )
            print("GPIO.setup({},GPIO.OUT)".format(cfg['pwmpin']))
            GPIO.setup(cfg["pwmpin"],GPIO.OUT)
            print("self.pwm= GPIO.PWM({},1000)".format(cfg['pwmpin']))
            cfg['pwm']= GPIO.PWM(cfg['pwmpin'],1000)
            print("cfg['pwm'].start(0)")
            cfg['pwm'].start(0)

            cfg['brightness']= 0 # 0-255 as used by HA, initially 0

            self.pwmlights[light]= cfg

        print("IoTraspipwmlight.__init__() done")

    def read_data(self) -> Dict:

        print("IoTraspipwmlight.read_data()")

        val = {}
        for light in self.pwmlights:
            val[light] = self.pwmlights[light]['brightness']

        print("IoTraspipwmlight.read_data() done ret ", val)

        return val


    def sensor_list(self) -> list:
        print("IoTraspipwmlight.sensor_list()")
        return []

    def set_state(self, messages: Dict) -> bool:
        """ Commands from Home Assistant MQTT arrive here """
        self.logger.debug("IoTraspipwmlight.setstate() %s", messages)
        print("IoTraspipwmlight.set_state() ", messages)

        for light in self.pwmlights:
            if light in messages:

                print("IoTraspipwmlight.set_state() light=", light )

                cfg= self.pwmlights[light]
                print("IoTraspipwmlight.set_state() cfg=", cfg )

                # determine new brightness settings

                msg= messages[light]
                if msg.isdigit():

                    print(" set light to ", int(msg))
                    cfg['brightness']= int(msg)

                elif msg == "ON":

                    print(" set light to ", msg)

                    if cfg['brightness'] > 0:
                        print("already ON")
                    else:
                        print("switching ON")
                        cfg['brightness']= 255

                elif msg == "OFF":

                    print(" set light to ", msg)
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

                    print("   APPLY brightness {} -> pwm {}".format(cfg['brightness'],pwm_duty_cycle))

                    # switch first pin to LOW and second pin to HIGH
                    GPIO.output(cfg['pins'][0],GPIO.LOW)
                    GPIO.output(cfg['pins'][1],GPIO.HIGH)


        # for cover in self.poscovers:
        #     if cover in messages:
        #         msg = messages[cover]
        #         oldstate = self.poscovers[cover]["status"]
        #         target= oldstate
        # 
        #         if msg.isdigit():
        # 
        #             target= int(msg)
        # 
        #         elif msg == self.conf["payload_open"]:
        # 
        #             target= 100
        # 
        #         elif msg == self.conf["payload_close"]:
        # 
        #             target= 0
        # 
        #         elif msg == self.conf["payload_stop"]:
        # 
        #             # this will set the new target value to the current state +/-1
        #             # thus it will not stop immediately but go one more time though
        #             # read_data() where motor_stop() will be called
        #             # (because motor_stop() cannot be called here safely)
        #             if target != oldstate:
        #                 if target > oldstate:
        #                     target= oldstate+1
        #                 else: # target < oldstate
        #                     target= oldstate-1
        # 
        #         else:
        #             self.logger.error("IoTraspipwmlight.set_state(): "
        #                               "unknown command %s", msg)
        # 
        #         self.poscovers[cover]["target"]= target
        # 
        #         if oldstate != target:
        # 
        #             self.runtime.trigger_for_device(self)


        print("IoTraspipwmlight.set_state() done")
        return False

    def shutdown(self, _) -> None:
        for i in pwmlights:

            for pin in self.conf["pins"]:
                GPIO.output(pin,GPIO.LOW)
            self.pwm.ChangeDutyCycle(0)
        # must not GPIO cleanup here because other devices might still want to reset things
        #GPIO.cleanup()


    def shutdown(self, _) -> None:
        print("IoTraspipwmlight.shutdown()")

        for light in self.pwmlights:
            cfg= self.pwmlights[light]
            # PWM pin off
            cfg['pwm'].ChangeDutyCycle(0)
            # power pins off
            for pin in cfg["pins"]:
                GPIO.output(pin,GPIO.LOW)


        # must not GPIO cleanup here because other devices might still want to reset things
        #GPIO.cleanup()
        print("IoTraspipwmlight.shutdown() done")

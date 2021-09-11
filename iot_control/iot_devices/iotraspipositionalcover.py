#!/usr/bin/python
# -*- coding: utf-8 -*-

""" Raspi cover device
"""
import time
import logging
from typing import Dict
import RPi.GPIO as GPIO
from iot_control.iotdevicebase import IoTDeviceBase
from iot_control.iotfactory import IoTFactory
import json

motorstep= []
motorstep.append( [ GPIO.HIGH, GPIO.LOW,  GPIO.HIGH, GPIO.LOW  ] )
motorstep.append( [ GPIO.LOW,  GPIO.HIGH, GPIO.HIGH, GPIO.LOW  ] )
motorstep.append( [ GPIO.LOW,  GPIO.HIGH, GPIO.LOW,  GPIO.HIGH ] )
motorstep.append( [ GPIO.HIGH, GPIO.LOW,  GPIO.LOW,  GPIO.HIGH ] )

@IoTFactory.register_device("raspi-positional-cover")
class IoTraspipositionalcover(IoTDeviceBase):
    """ Cover pr garage door with two input GPIO pins for detecting the
    closed and open states and one output GPIO pin triggering the motor
    controller
    """

    logger = None

    # stores mapping of covers to pins
    poscovers = {}

    # handle for a pending autooff event
    handle = None

    def __init__(self, **kwargs):
        super().__init__()

        setupdata = kwargs.get("config")
        self.logger = logging.getLogger("iot_control")
        self.logger.debug("IoTraspipositionalcover.__init__()")

        self.conf = setupdata
        
        GPIO.setmode(GPIO.BCM)  # GPIO Nummern statt Board Nummern
        GPIO.setwarnings(False)

        self.step= setupdata["position_open"] // 100
        self.sleeptime= setupdata["sleeptime"] * 0.001

        self.state_file= setupdata["state_file"]

        covers_cfg = setupdata["poscovers"]

        for cover in covers_cfg:

            cfg = covers_cfg[cover]


            for pin in cfg["motorpins"]:
                GPIO.setup(pin,GPIO.OUT)

            cfg["payload_open"]= setupdata["payload_open"]
            cfg["payload_close"]= setupdata["payload_close"]
            cfg["payload_stop"]= setupdata["payload_stop"]


            #self.logger.info("new IoTraspipositionalcover device with input pins %d, %d "
                # "and output pin %d, initial state %s ", pin_down, pin_up, pin_trigger)

            cfg["status"]= 0
            cfg["target"]= 0

            self.poscovers[cover] = cfg

        # read the old state if present
        val = {}
        with open(self.state_file,"r") as f:
            val= json.load(f)

            for cover in covers_cfg:
                self.poscovers[cover]["status"]= val[cover]
                self.poscovers[cover]["target"]= val[cover]

    #as for four phase stepping motor, four steps is a cycle. the function is used to drive the stepping motor clockwise or anticlockwise to take four steps    
    def move_one_period(self,direction,ms, motorpins):
        for j in range(0,4,1):      #cycle for power supply order

            if 0 == direction:
                jj= j
            else:
                jj= 3-j

            for i in range(0,4,1):  #assign to each pin, a total of 4 pins
                GPIO.output( motorpins[i], motorstep[jj][i] )

            if(ms<0.003):       #the delay can not be less than 3ms, otherwise it will exceed speed limit of the motor
                ms = 0.003
            time.sleep(ms)

    #continuous rotation function, the parameter steps specifies the rotation cycles, every four steps is a cycle
    def move_steps(self,direction, ms, steps, motorpins):

        for i in range(steps):
            self.move_one_period(direction, ms, motorpins)

    def motor_stop(self, motorpins):

        for p in motorpins:
            GPIO.output(p,GPIO.LOW)

    def read_data(self) -> Dict:

        val = {}
        changed= False # at least one cover changed
        for cover in self.poscovers:

            # if the status is != the target value, then this is the place to act
            # it will make the cover move a small bit here bevore returning the new value
            # and then triggering the runtime to call our read_data() again very soon
            if self.poscovers[cover]["target"] != self.poscovers[cover]["status"]:

                changed= True

                if self.poscovers[cover]["target"] > self.poscovers[cover]["status"]:

                    delta= 1
                    self.move_steps( 0, self.sleeptime, delta*self.step, self.poscovers[cover]["motorpins"] )
                    self.poscovers[cover]["status"] += delta
                    val[cover] = self.poscovers[cover]["status"]

                elif self.poscovers[cover]["target"] < self.poscovers[cover]["status"]:
            
                    delta= 1
                    self.move_steps( 1, self.sleeptime, delta*self.step, self.poscovers[cover]["motorpins"] )
                    self.poscovers[cover]["status"] -= delta
                    val[cover] = self.poscovers[cover]["status"]

                ## are we don moving now? Then stop motor for this cover
                if self.poscovers[cover]["target"] == self.poscovers[cover]["status"]:

                    self.motor_stop( self.poscovers[cover]["motorpins"] )
    
                # if one poscover was moved one step, don't go on to the next but break the cover loop
                # this makes one cover move to the final position before the next starts moving
                # which is much nicer and smoother
                break

        
        needtochange= False # at least one cover that needs to change some more?
        for cover in self.poscovers:

            if self.poscovers[cover]["target"] != self.poscovers[cover]["status"]:

                needtochange= True

            val[cover] = self.poscovers[cover]["status"]


        if needtochange:

            self.runtime.trigger_for_device(self)

        else:

            if changed:

                # only if something changed and there are no scheduled further changes on another cover
                # safe the states out to state_file, where it can be read in in __init__() after a restart
                # this avoids too frequent write operation which the SD card wounldn't like so much
                with open(self.state_file,'w') as f:
                    json.dump(val,f)

                # need to trigger on last time so that the target value gets transfered
                self.runtime.trigger_for_device(self)

        return val

    def sensor_list(self) -> list:
        return self.poscovers.keys()

    def set_state(self, messages: Dict) -> bool:
        """ Commands from Home Assistant MQTT arrive here """
        self.logger.debug("IoTraspipositionalcover.setstate() %s", messages)

        for cover in self.poscovers:
            if cover in messages:
                msg = messages[cover]
                oldstate = self.poscovers[cover]["status"]
                target= oldstate

                if msg.isdigit():

                    target= int(msg)

                elif msg == self.conf["payload_open"]:

                    target= 100

                elif msg == self.conf["payload_close"]:

                    target= 0

                elif msg == self.conf["payload_stop"]:

                    # this will set the new target value to the current state +/-1
                    # thus it will not stop immediately but go one more time though
                    # read_data() where motor_stop() will be called
                    # (because motor_stop() cannot be called here safely)
                    if target != oldstate:
                        if target > oldstate:
                            target= oldstate+1
                        else: # target < oldstate
                            target= oldstate-1

                else:
                    self.logger.error("IoTraspipositionalcover.set_state(): "
                                      "unknown command %s", msg)

                self.poscovers[cover]["target"]= target

                if oldstate != target:

                    self.runtime.trigger_for_device(self)


        # return False so that the mqtthass will _not_ publish the updated
        # state right away
        return False

    def shutdown(self, _) -> None:
        for cover in self.poscovers:
            cfg = self.poscovers[cover]
            for pin in cfg["motorpins"]:
                GPIO.output(pin,GPIO.LOW)
        # must not GPIO cleanup here because other devices might still want to reset things
        #GPIO.cleanup()

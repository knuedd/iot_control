#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" definitions for an bubble sensor measuring water level height
"""

from typing import Dict
import logging
from iot_control.iotdevicebase import IoTDeviceBase
from iot_control.iotfactory import IoTFactory


@IoTFactory.register_device("bubblesensor")
class IoTbubblesensor(IoTDeviceBase):
    """ bubble sensor class
    """

    def __init__(self, **kwargs):
        super().__init__()
        setupdata = kwargs.get("config")
        self.conf = setupdata
        self.valve_pin = setupdata["valve_pin"] # pin to trigger to close the air valve
        self.pump_pin = setupdata["pump_pin"] # pin to trigger to start the pump
        self.hx711_dout = setupdata["dout"] # dout pin for HX711
        self.hx711_sck = setupdata["sck"] # sck pin for HX711
        self.coeff_linear = float( setupdata["coeff_linear"] ) # linear coefficient from least square calibration
        self.coeff_const = float( setupdata["coeff_const"] ) # absolute coefficienct from least square calibration
        self.offset = float( setupdata["offset"] ) # positive or negative offset of water level in mm
        self.period = float( setupdata["period"] ) # time between measurements in s

        self.logger= logging.getLogger("iot_control")

        # variables transporting new values
        self.waterlevel_total= -1.0
        self.waterlevel_net= -1.0
        self.pressure_before= 0.0
        self.pressure_bubbles= 0.0
        self.have_new_value= False

        # TODO start background thread doing the measurement which needs several seconds
        # TODO make sure that the thread does its job regularly or is scheduled every time
        # for the next time ... don't know yet which is better

    def read_data(self) -> Dict:
        """ read data """

        val= {}

        # don't do anything here but wait for background thread to 
        # provide new values and then set have_new_values to True

        if self.have_new_value:

            val = {
                "waterlevel_total": "{:.1f}".format(data.temperature),
                "waterlevel_net": "{:.1f}".format(data.humidity),
                "pressure_before": "{:.1f}".format(data.humidity),
                "pressure_bubbles": "{:.1f}".format(data.humidity)

            self.have_new_value= False
        }

        return val

    def sensor_list(self) -> list:
        return ["waterlevel_total", "waterlevel_net", "pressure_before", "pressure_bubbles"]

    def set_state(self, _) -> bool:
        """ nothing can be set here """

    def shutdown(self, _) -> None:
        """ nothing to do """

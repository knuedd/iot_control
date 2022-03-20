#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" definitions for an PCF8591 pulse sensor
"""

from typing import Dict
import logging
import socket
import smbus
import threading
import time
import json
from iot_control.iotdevicebase import IoTDeviceBase
from iot_control.iotfactory import IoTFactory

import paho.mqtt.client as mqtt


@IoTFactory.register_device("pcf8591pulses")
class IoTpcf8591pulses(IoTDeviceBase):
    """ PCF8591Oulses sensor class
    """

    def internal_background_thread(self):

        bus=smbus.SMBus( self.port )
        cmd=0x40
        num= len(self.values)
        sleeptime= 0.010

        currvalue= {}
        lastvalue= {}
        for i in self.values:
            currvalue[i]= 0
            lastvalue[i]= 255

        while True:

            for i in self.values:
                lastvalue[i]= currvalue[i]
                currvalue[i]= bus.read_byte_data(self.address,cmd+self.channels[i])

                #print( "   ", i, lastvalue[i], currvalue[i] )

                if currvalue[i] < lastvalue[i] // 2 :
                    self.values[i] += self.factors[i]

            time.sleep(sleeptime)

    def mqtt_callback_connect(self, client, userdata, flags, rc):
        """ callback as defined by the mqtt API for the moment when the connection is made
        """
        (result, _) = self.mqtt_client.subscribe( self.mqtt_topic_periodic )
        self.logger.info( "MQTT for IoTpcf8591pulses: subscription result for {}: {}".format(self.mqtt_topic,result) )
        (result, _) = self.mqtt_client.subscribe( self.mqtt_topic_reset )
        self.logger.info( "MQTT for IoTpcf8591pulses: subscription result for {}: {}".format(self.mqtt_topic,result) )


    # The callback for when a PUBLISH message is received from the server.
    def mqtt_callback_message( self, client, userdata, msg ):
        """ callback from mqtt in case message arrives """

        if msg.topic == self.mqtt_topic :

            self.logger.warning( "IoTpcf8591pulses.mqtt_callback_message() '{}' with payload '{}', adopting values".format( msg.topic, msg.payload ) )
            payload = json.loads( msg.payload )  ##msg.payload.decode("utf-8")
            for i in payload:
                if i in self.values:
                    newval= float( payload[i] )
                    self.logger.warning( "    old value {}, new value {}, delta {}".format( self.values[i], newval, ( newval - self.values[i] ) ) )
                    self.values[i]= newval

            # change the accepted topic, only for the very first one it is going to listen to
            # self.mqtt_topic_periodic. From the second time on it is only listening to self.mqtt_topic_reset
            self.mqtt_topic= self.mqtt_topic_reset
            
            self.mqtt_client.unsubscribe( self.mqtt_topic_periodic )

        else :
            self.logger.warning( "IoTpcf8591pulses.mqtt_callback_message() unexpected message '{}' '{}' ignored".format( msg.topic, msg.payload ))


    def mqtt_callback_disconnect(self, client, userdata, rc):
        """ mqtt callback when the client gets disconnected """
        if rc != 0:
            self.logger.warning( "MQTT for IoTpcf8591pulses: unexpected disconnection." )


    def __init__(self, **kwargs):
        super().__init__()
        setupdata = kwargs.get("config")
        self.conf = setupdata
        self.logger= logging.getLogger("iot_control")
        self.port = setupdata["port"]
        self.address = setupdata["i2c_address"]

        # for optional feature to retain values across restarts via MQTT
        self.mqtt_topic_periodic= "iotpcf8591pulses/periodic"
        self.mqtt_topic_reset= "iotpcf8591pulses/reset"
        self.mqtt_topic= self.mqtt_topic_periodic # this is the topic it is currently listening to

        self.mqtt_client= None
        self.retain= False

        if "internal_mqtt_server" in setupdata and "internal_mqtt_port" in setupdata and "internal_mqtt_user" in setupdata and "internal_mqtt_password" in setupdata :

            self.retain= True

        self.values= {}
        self.factors= {}
        self.channels= {}
        for s in setupdata["sensors"]:
            self.values[s]= setupdata["sensors"][s]["recentvalue"]
            self.factors[s]= setupdata["sensors"][s]["factor"]
            self.channels[s]= setupdata["sensors"][s]["channel"]

        # if there are values from the MQTT channel then the recent values from the config above are ignored
        if True == self.retain :

            self.mqtt_client= mqtt.Client(client_id="iot_control_pcf8591pulse_"+str(socket.gethostname()))
            self.mqtt_client.on_connect = self.mqtt_callback_connect
            self.mqtt_client.on_message = self.mqtt_callback_message
            self.mqtt_client.on_disconnect = self.mqtt_callback_disconnect
            self.logger.info("connection to mqtt server")


            self.mqtt_client.username_pw_set( username= setupdata['internal_mqtt_user'], 
                                              password= setupdata['internal_mqtt_password'] )
            self.mqtt_client.connect( setupdata['internal_mqtt_server'], setupdata['internal_mqtt_port'], keepalive= 60 )
            self.mqtt_client.loop_start()

        self.t= threading.Thread( target=background_thread, args=(self,), daemon= True )
        self.t.start()

 
    def read_data(self) -> Dict:

        val= {}
        for i in self.values:
            val[i]= "{:.3f}".format(self.values[i])

        if True == self.retain :

            payload = json.dumps(val)
            self.logger.info("MQTT for IoTpcf8591pulses publishing: %s", payload)
            result = self.mqtt_client.publish( self.mqtt_topic_periodic, payload, retain=True )

        return val


    def sensor_list(self) -> list:
        self.logger.warning("IoTpcf8591pulses.sensor_list(): THIS IS NEVER CALLED, IS IT?")
        return self.values.keys()


    def set_state(self, _) -> bool:
        """ nothing can be set here """

    def shutdown(self, _) -> None:
        """ nothing to do """

# must not be a method
def background_thread( obj ):

    obj.internal_background_thread()


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

        print("    internal_background_thread ", num, " values" )

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
                    #print( "pulse" )
                    self.values[i] += self.factors[i]
                #else:
                #    print( "_" )

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

            print( "IoTpcf8591pulses.mqtt_callback_message() ", msg.topic, msg.payload )
            print( "    adopting external values", msg.payload )
            print( "       values before: ", self.values )
            payload = json.loads( msg.payload )  ##msg.payload.decode("utf-8")
            print( "       external values decoded", msg.payload )
            for i in payload:
                if i in self.values:
                    self.values[i]= float( payload[i] )
                    
            print( "       values after: ", self.values )

            # change the accepted topic, only for the very first one it is going to listen to
            # self.mqtt_topic_periodic. From the second time on it is only listening to self.mqtt_topic_reset
            self.mqtt_topic= self.mqtt_topic_reset

        else :
            print( "IoTpcf8591pulses.mqtt_callback_message() ", msg.topic, msg.payload, " IGNORED " )


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
            print( "       retaining enabled" )

        else:
            print( "       retaining disabled" )

        print( "IoTpcf8591pulses.__init__: ", setupdata )

        self.values= {}
        self.factors= {}
        self.channels= {}
        for s in setupdata["sensors"]:
            print( "    ", s, " --> ", setupdata["sensors"][s] )
            self.values[s]= setupdata["sensors"][s]["recentvalue"]
            self.factors[s]= setupdata["sensors"][s]["factor"]
            self.channels[s]= setupdata["sensors"][s]["channel"]

        print( "    sensors: ", self.values.keys(), " ====================" )
        print( "        values:   ", self.values )
        print( "        factors:  ", self.factors )
        print( "        channels: ", self.channels )


        # if there are values from the MQTT channel then the recent values from the config above are ignored
        print( "    TODO: try to read last values from separate MQTT channel" )
        if True == self.retain :

            print( "       prepare retaining functionality" )

            self.mqtt_client= mqtt.Client(client_id="iot_control_pcf8591pulse_"+str(socket.gethostname()))
            print( "       A" )
            self.mqtt_client.on_connect = self.mqtt_callback_connect
            print( "       B" )
            self.mqtt_client.on_message = self.mqtt_callback_message
            print( "       C" )
            self.mqtt_client.on_disconnect = self.mqtt_callback_disconnect
            print( "       D" )
            self.logger.info("connection to mqtt server")
            print( "       E" )


            self.mqtt_client.username_pw_set( username= setupdata['internal_mqtt_user'], 
                                              password= setupdata['internal_mqtt_password'] )
            print( "       F" )
            self.mqtt_client.connect( setupdata['internal_mqtt_server'], setupdata['internal_mqtt_port'], keepalive= 60 )
            print( "       G" )
            self.mqtt_client.loop_start()
            print( "       Z" )


        print( "    TODO: done reading last values from separate MQTT channel" )


        print( "going to start background thread" )
     
        self.t= threading.Thread( target=background_thread, args=(self,), daemon= True )
        self.t.start()

        print( "background thread has started" )

 
    def read_data(self) -> Dict:

        print( "read_data() ", self.values )

        val= {}
        for i in self.values:
            val[i]= "{:.3f}".format(self.values[i])

        if True == self.retain :
            print( "    TODO: save current values to separate MQTT channel" )

            payload = json.dumps(val)
            self.logger.info("MQTT for IoTpcf8591pulses publishing: %s", payload)
            print( "MQTT for IoTpcf8591pulses publishing: ", self.mqtt_topic_periodic, payload )
            result = self.mqtt_client.publish( self.mqtt_topic_periodic, payload, retain=True )
            print( "MQTT for IoTpcf8591pulses publishing: done, result ", result )


            print( "    TODO: check for external reset message from MQTT to reset the values by force" )


            print( "    TODO: done checking for external reset message from MQTT to reset the values by force" )


        return val

    def sensor_list(self) -> list:
        print("THIS IS NEVER CALLED, IS IT?")
        return self.values.keys()

    def set_state(self, _) -> bool:
        """ nothing can be set here """

    def shutdown(self, _) -> None:
        """ nothing to do """

# must not be a method
def background_thread( obj ):

    print( "me background thread: A " )

    obj.internal_background_thread()

    print( "me background thread: Z " )

#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" IOT runtime class

"""

import sys
import logging
import asyncio
import functools
import signal
import yaml
import iot_control.iot_devices.iotads1115
import iot_control.iot_devices.iotbme280
import iot_control.iot_devices.iotbh1750
import iot_control.iot_devices.iotraspigpio
import iot_control.iot_devices.iotcommandswitch
import iot_control.iot_devices.iotraspibinarysensor
import iot_control.iot_devices.iotraspistatecover
import iot_control.iot_devices.iotraspipositionalcover
import iot_control.backends.influx
import iot_control.backends.mqtthass
from iot_control.iotfactory import IoTFactory


class IoTRuntime:
    """ this is the runtime class that will load the setup
        and put backends and sensors together and runs the
        main loop
    """
    backends = []
    devices = []
    update_intervall = 60
    loop = None

    def __init__(self, configfile: str, log_level=logging.WARNING):

        self.logger = logging.getLogger('iot_control')
        self.logger.setLevel(log_level)
        filehandler = logging.FileHandler('iot_control.log')
        filehandler.setLevel(log_level)
        self.logger.addHandler(filehandler)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        filehandler.setFormatter(formatter)
        self.logger.addHandler(filehandler)
        # logger.debug('Debug-Nachricht')
        # logger.info('Info-Nachricht')
        # logger.warning('Warnhinweis')
        # logger.error('Fehlermeldung')
        # logger.critical('Schwerer Fehler')

        self.logger.info("loading config file %s", configfile)
        with open(configfile, 'r') as stream:
            try:
                self.conf = yaml.load(stream, Loader=yaml.SafeLoader)
            except yaml.YAMLError as exc:
                self.logger.critical(exc)
                self.logger.critical(
                    "Unable to parse configuration file %s", configfile)
                sys.exit(1)
        # first: build backends
        for backend in self.conf["backends"]:
            self.logger.info("creating backend %s", backend)
            backend_cfg = self.conf["backends"][backend]
            try:
                self.backends.append(IoTFactory.create_backend(
                    backend, config=backend_cfg))
            except Exception as exception:
                self.logger.error(
                    "error creating backend: %s", exception)
        sys.stdout.flush()
        if not self.backends:
            self.logger.critical("no backends available")
            sys.exit(1)
            # second: register devices with backend
        for device in self.conf["devices"]:
            self.logger.info("creating device %s", device)
            device_cfg = self.conf["devices"][device]
            try:
                real_device = IoTFactory.create_device(
                    device, config=device_cfg)
                real_device.give_runtime_reference(self)
                self.devices.append(real_device)
                for backend in self.backends:
                    backend.register_device(real_device)
            except Exception as exception:
                self.logger.error(
                    "error creating device: %s", exception)
        for backend in self.backends:
            backend.announce()

    def set_intervall(self, new_intervall: int):
        """ sets the intervall between two readings of the sensors

        Args:
            new_intervall (int): the new interval in seconds between
            readings of the sensors
        """
        self.update_intervall = new_intervall

    def signal_handler(self, signame, loop):
        """ catches signals and finishes the main loop

        Args:
            signame: the incoming signal
            loop: reference to the loop
        """
        self.logger.info("got signal %s: exit", signame)
        loop.stop()

    def regular_update(self, loop):
        """ do the regular update for all passive devices
        """
        self.logger.debug("iotruntime.regular_update()")
        for device in self.devices:
            data = device.read_data()
            
            if data:
                for backend in self.backends:
                    backend.workon(device, data)

        # reschedule myself for next time
        loop.call_later(self.update_intervall,
                        IoTRuntime.regular_update, self, loop)

    def scheduled_update(self, device, switch, event):
        """ handler for updates, call from the main event handler

        Args:
            device (IOTdevicebase): the device
            switch (str): the switch on the device
            event (str): the message to send
        """
        if device.set_state({switch: event}):
            for backend in self.backends:
                data = device.read_data()
                backend.workon(device, data)


    def __schedule_from_local_thread(self,delay,device,switch,event):
        """ private helper method to schedule a future event from the local thread 
            (the thread belonging to the event loop) and pass the handle for the 
            delayed event back to the device

        Args:
            delay (int): delay when this should be send in seconds
            device (IOTdevicebase): the device
            switch (str): the switch name on the device
            event (str): which text to send

        """

        handle= self.loop.call_later(delay,functools.partial(IoTRuntime.scheduled_update,self,device,switch,event))
        device.give_scheduled_event_handle(handle,switch)
    
    def schedule_for_device(self,delay,device,switch,event):
        """ Schedule an event for a device, mainly to be used with
            mqtt

        Args:
            delay (int): delay when this should be send in seconds
            device (IOTdevicebase): the device
            switch (str): the switch name on the device
            event (str): which text to send

        """
        
        if self.loop is None:
            self.logger.error("no event loop created, must not call 'IoTRuntime.schedule_for_device()' yet")
            return None
       
        # this may look strange but needs to be that way! This function 'schedule_for_device()' is likely called 
        # from other threads such as an MQTT handler. That's why 'call_soon_threadsafe()' is scheduling the 
        # following step in the thread of the main event loop soon. And then 'call_later(delay,...)' get's
        # properly scheduled over there in the thread of the main event loop.
        self.loop.call_soon_threadsafe(
            functools.partial(IoTRuntime.__schedule_from_local_thread,self,delay,device,switch,event))
        
    def triggered_update(self, device):
        """ handler for trigger_for_device(), call from the main event handler

        Args:
            device (IOTdevicebase): the device
            switch (str): the switch on the device
            event (str): the message to send
        """
        for backend in self.backends:
            data = device.read_data()
            backend.workon(device, data)

    def trigger_for_device(self,device):
        """ Act on notification by a device, like schedule_for_device() but without a delay,
            it makes the runtime call workon() for this device, mainly to be used with mqtt

        Args:
            device (IOTdevicebase): the device
        """
        if self.loop is None:
            self.logger.error("no event loop created, must not call 'IoTRuntime.schedule_for_device()' yet")
            return None
       
        # This get's (most likely) called from another thread such as a GPIO callback thread but
        # not the thread where self.loop lives in. Therefore, the following call makes self.loop()
        # to call self.trigger_for_device() soon inside the thread of self.loop
        self.loop.call_soon_threadsafe(functools.partial(IoTRuntime.triggered_update,self,device))

    def loop_forever(self):
        """ the main loop of the runtime
        """
        self.logger.info(
            "starting main loop with %d seconds intervall", int(self.update_intervall))
        self.loop = asyncio.get_event_loop()

        # install signal handlers for graceful exit
        for signame in {'SIGINT', 'SIGTERM'}:
            self.loop.add_signal_handler(getattr(signal, signame),
                                         functools.partial(IoTRuntime.signal_handler, self, signame, self.loop))

        # schedule regular update for the first time
        self.loop.call_soon(IoTRuntime.regular_update, self, self.loop)

        try:
            self.loop.run_forever()
        except:
            self.logger.error("unexpected error via exception")
        finally:
            self.loop.close()

        for device in self.devices:
            device.shutdown(None)

        for backend in self.backends:
            backend.shutdown()

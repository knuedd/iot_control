# Connect your IoT devices

This project provides a framework to easily connect IoT devices (sensors and switches) with different backends. It allows to include more backends and devices.

## Supported devices:
* [BME280 sensor](https://www.amazon.de/Adafruit-Temperature-Humidity-Pressure-ADA2652/dp/B013W0RR6Y): humidity, air pressure, temperature
* [ADS1115 sensor](https://www.amazon.de/Adafruit-ads1115-16-Bit-Channel-programmierbar-Verst%C3%A4rken/dp/B00QIW4MGW/ref=sr_1_2?__mk_de_DE=%C3%85M%C3%85%C5%BD%C3%95%C3%91&dchild=1&keywords=ads1115+adafruit&qid=1609321159&sr=8-2): analog digital converter
* [BH1750](https://www.amazon.de/AZDelivery-GY-302-Helligkeitsensor-Arduino-Raspberry/dp/B07QBPRZH1/ref=sr_1_1_sspa?dchild=1&keywords=bh1750&qid=1609321202&sr=8-1-spons&psc=1&spLa=ZW5jcnlwdGVkUXVhbGlmaWVyPUEyVkI3SDNHSzFYRFFRJmVuY3J5cHRlZElkPUEwNjExNjQwM1NBR1dFMVJSNE01UyZlbmNyeXB0ZWRBZElkPUEwOTg0NzIxVklHUFVDSE8zQkIzJndpZGdldE5hbWU9c3BfYXRmJmFjdGlvbj1jbGlja1JlZGlyZWN0JmRvTm90TG9nQ2xpY2s9dHJ1ZQ==): illuminance
* [Raspberry PI GPIO switches](https://learn.sparkfun.com/tutorials/raspberry-gpio/all): drive GPIO pins on the raspberry pi. To actually drive the pins you need to use the mqtt-hass backend.
* Shell command switches: run shell commands when a switch is clicked in Home Assistant. Has an 'on' and an 'off' command.
* Raspberry PI cover for garage doors or covers as defined by Home Assistant. It uses two input pins to detect the closed or opened state of the cover and one output pin which triggers a pulse so that the garage door motor is put into action.

## Supported backends:

Backends can set and read states if the functionality of the software used provides this. Pure database backends like influx will only store the values from the sensors.

* [Home Assistant with MQTT discovery](https://www.home-assistant.io/docs/mqtt/discovery/): works for sensors and switches
* [InfluxDB](https://en.wikipedia.org/wiki/InfluxDB): works for sensors only, will ignore switches

## Prerequisites

* Install .deb packages: 'sudo apt install python3-yaml'
* Install  PIP packages: 'pip3 install smbus smbus2 RPi.GPIO rpi.bme280 paho-mqtt influxdb'

Hint: On Raspbian GNU/Linux 9.13 (stretch) don't use the .deb package 'python3-influxdb' but the much newer pip3 package 'influxdb'

## How to get started:

1. Get some sensors and a small device to run the sensors on. The device should be able to run python.
2. Make sure you habe a suitable backend that will store the data or interact with the sensors. That's why you are here, right? So maybe you have an Home Assistant installation already. Then please check that [mqtt is enabled](https://www.home-assistant.io/integrations/mqtt/). Otherwise: get one or get an InfluxDB instance.
3. Clone this project at the device and copy the example setup to a setup.yaml and edit the content of the setup file according to your needs.
4. Run rooftop.py. Maybe with a screen session, but much better as a service (via systemd).

## I need support for more backends and more sensors

Send me a message, I'll write this when its needed. It should be easy to add more of both kinds.

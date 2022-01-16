#!/bin/bash

# set explicit values to iotpcf8591pulses

TOPIC="iotpcf8591pulses/reset"

eval HOST=`grep "internal_mqtt_server:" setup.yaml | awk '{print $2}'`
eval PORT=`grep "internal_mqtt_port:" setup.yaml | awk '{print $2}'`
eval USER=`grep "internal_mqtt_user:" setup.yaml | awk '{print $2}'`
eval PASS=`grep "internal_mqtt_password:" setup.yaml | awk '{print $2}'`

COUNTER="stromzaehler"
VALUE="9999.888"


if [ -z $1 ]; then
    echo "Counter name not given, e.g. 'stromzaehler' or 'heizungsstromzaehler'"
    exit 1
fi
    
if [ -z $2 ]; then
    echo "Value not given, e.g. 1000.0"
    exit 1
fi

COUNTER=$1

re='^[0-9]+([.][0-9]+)?$'
if ! [[ $2 =~ $re ]] ; then
   echo "Second parameter is not a number"
   exit 1
fi

VALUE=$2

#MESSAGE="{\"stromzaehler\": \"3222.494\", \"heizungsstromzaehler\": \"6444.705\"}"
MESSAGE="{\""$COUNTER"\": \""$VALUE"\"}"

echo mosquitto_pub --topic $TOPIC  -u $USER -P $PASS -h $HOST -p $PORT -m "$MESSAGE"
mosquitto_pub --topic $TOPIC  -u $USER -P $PASS -h $HOST -p $PORT -m "$MESSAGE"

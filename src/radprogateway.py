#!/usr/bin/env python3

import time
import serial
import paho.mqtt.client as mqtt
import json
import os
import sys


missing=[v for v in ("BROKER", "TOPIC", "SERIAL_PORT") if not os.environ.get(v)]
if missing:
    sys.exit("Fehler: Umgebungsvariable(n) nicht gesetzt: "+", ".join(missing))

loopdelay=60 #seconds
min_value=999.99
max_value=0.0


def get_tubeRate(myser):
    myser.write(b"GET tubeRate\r\n")
    retval=myser.read(20).decode("utf-8", errors="replace")
    #print(retval)
    retval2=retval.split(" ")
    if(retval2[0]=="OK"):
        return(retval2[1][:-2])

def get_tubePulseCount(myser):
    myser.write(b"GET tubePulseCount\r\n")
    retval=myser.read(20).decode("utf-8", errors="replace")
    #print(retval)
    retval2=retval.split(" ")
    if(retval2[0]=="OK"):
        return(int(retval2[1][:-2]))


def get_tubeSensitivity(myser):
    myser.write(b"GET tubeSensitivity\r\n")
    retval=myser.read(20).decode("utf-8", errors="replace")
    #print(retval)
    retval2=retval.split(" ")
    if(retval2[0]=="OK"):
        return(float(retval2[1][:-2]))


ser = serial.Serial(
    port=os.environ["SERIAL_PORT"],
    baudrate=115200,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=0.1
)


mydata= {
 "Dosisleistung":9999,
 "Aktivitaet":9998,
 "Sensitivitaet":9999,
 "MinDosisleistung":9999.0,
 "MaxDosisleistung":0.0
}

print("Welcome to Radprogateway")

broker = os.environ["BROKER"]
port = int(os.environ.get("MQTT_PORT", "1883"))
topicgrp = os.environ["TOPIC"]

client = mqtt.Client()

client.will_set(
    topic=topicgrp+"/status",
    payload="offline",
    qos=1,
    retain=True
)

client.connect(broker, port)
client.publish(topicgrp+"/status", "online", qos=1, retain=True, properties=None)

ser.isOpen()

sensitivity=get_tubeSensitivity(ser)
print("Sensitivity: "+str(sensitivity)+ " cpm/uSv/h")
cnt_old=get_tubePulseCount(ser)

while(1):
    time.sleep(60)
    cnt_new=get_tubePulseCount(ser)
    current_cpm=cnt_new-cnt_old
    print("Eventhaeufigkeit: "+str(current_cpm)+" cpm")
    current_value=round(current_cpm/sensitivity,3)
    if current_value>max_value:
     max_value=current_value
    if current_value<min_value:
     min_value=current_value
    print("Dosisleistung: "+str(current_value)+" uSv/h")
    cnt_old=cnt_new
    mydata["Dosisleistung"]=current_value
    mydata["Aktivitaet"]=current_cpm
    mydata["Sensitivitaet"]=sensitivity
    mydata["MinDosisleistung"]=min_value
    mydata["MaxDosisleistung"]=max_value
    json_string = json.dumps(mydata)
    print(json_string)
    client.publish(topicgrp+"/data", json_string)

    print("----------------------------------------------------------------")


ser.close()

#!/usr/bin/env python3

import time
import serial
import paho.mqtt.client as mqtt
import json
import os
import sys


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


mydata= {
 "Dosisleistung":9999,
 "Aktivitaet":9998,
 "Sensitivitaet":9999,
 "MinDosisleistung":9999.0,
 "MaxDosisleistung":0.0
}

print("Welcome to Radprogateway")

# Alle Startprüfungen ausführen und Fehler sammeln, damit im Log alle Probleme auf einmal sichtbar sind
errors=[]

def report(msg):
    errors.append(msg)
    print(msg, file=sys.stderr, flush=True)

serial_port = os.environ.get("SERIAL_PORT")
broker = os.environ.get("BROKER")
topicgrp = os.environ.get("TOPIC")

for name, value in (("BROKER", broker), ("TOPIC", topicgrp), ("SERIAL_PORT", serial_port)):
    if not value:
        report("Fehler: Umgebungsvariable "+name+" ist nicht gesetzt")

try:
    port = int(os.environ.get("MQTT_PORT", "1883"))
except ValueError:
    port = 1883
    report("Fehler: MQTT_PORT '"+os.environ["MQTT_PORT"]+"' ist keine gültige Zahl")

ser = None
if serial_port:
    try:
        ser = serial.Serial(
            port=serial_port,
            baudrate=115200,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=0.1
        )
    except (serial.SerialException, OSError, ValueError) as e:
        report("Fehler: Serielle Schnittstelle '"+serial_port+"' kann nicht geöffnet werden: "+str(e)
               +"\nPrüfen: Existiert das Gerät auf dem Node? Stimmt SERIAL_PORT? Ausreichende Rechte (privileged)?")

client = mqtt.Client()
if broker and topicgrp:
    client.will_set(
        topic=topicgrp+"/status",
        payload="offline",
        qos=1,
        retain=True
    )
    try:
        client.connect(broker, port)
    except (OSError, ValueError) as e:
        report("Fehler: Verbindung zum MQTT-Broker '"+broker+":"+str(port)+"' fehlgeschlagen: "+str(e)
               +"\nPrüfen: Stimmen BROKER und MQTT_PORT? Ist der Broker vom Cluster aus erreichbar (DNS, Firewall)?")

sensitivity=None
if ser is not None:
    sensitivity=get_tubeSensitivity(ser)
    if sensitivity is None:
        report("Fehler: Keine gültige Antwort des Messgeräts auf '"+serial_port+"'. "
               "Ist das richtige Gerät angeschlossen und die Baudrate (115200) korrekt?")

if errors:
    sys.exit("Start abgebrochen wegen "+str(len(errors))+" Fehler(n), siehe oben.")

client.publish(topicgrp+"/status", "online", qos=1, retain=True, properties=None)
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

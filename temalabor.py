#!/usr/bin/env python
from qrtools import QR
from picamera import PiCamera
import paho.mqtt.client as mqtt
import subprocess
import sys


# if argument passed to enable camera picture, then save it as a flag
enableCameraPreview = False
if (len(sys.argv) >= 2) and sys.argv[1] == "--preview":
    enableCameraPreview = True

image_path = '/home/pi/ram/buffer_image.bmp'

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print(msg.topic+" "+str(msg.payload))

# initialize mqtt client
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect("192.168.1.128", 1883, 60)
client.loop_start()

# initialize camera
camera = PiCamera()
camera.rotation = 180
camera.framerate = 40
camera.resolution = (640, 480)

# enable camera
if enableCameraPreview:
    camera.start_preview()

# create qr decoder before loop
myCode = QR(filename=image_path)

# save last readed code to prevent multiple mqtt messages
lastQrCode = None


def get_qr_code_from_camera():
    camera.capture(image_path, 'bmp', use_video_port=True)

    # try to decode image
    if myCode.decode():
        print(myCode.data)
        return myCode.data
    else:
        print("QR code not found")
        return None


def qr_code_found(qrCode):
    global lastQrCode
    # first, split text by dash
    cmd = qrCode.split('-')

    # if command not consist exactly two part, then halt the program
    if len(cmd) != 2:
        return

    # we only send mqtt message once
    if qrCode == lastQrCode:
        return

    lastQrCode = qrCode

    # first part will be the number of the esp to open or close
    # second part will be the command itself (close or open)

    if cmd[1] == "open":
        # sending mqtt message immediately
        client.publish("esp{0}".format(cmd[0]), cmd[1])

        # call subprocess to show on pihat
        subprocess.call(["python", "/home/pi/pihat.py", "OFF"])

    elif cmd[1] == "close":
        # sending mqtt message immediately
        client.publish("esp{0}".format(cmd[0]), cmd[1])

        # call subprocess to clear pihat display
        subprocess.call(["python", "/home/pi/pihat.py", cmd[0]])


try:
    while True:
        qrCode = get_qr_code_from_camera()
        if qrCode is not None:
            # first, call qr code handler function
            qr_code_found(qrCode)
            print(qrCode)

            if enableCameraPreview:
                camera.annotate_text = qrCode

except KeyboardInterrupt:
    pass

# disable camera
if enableCameraPreview:
    camera.stop_preview()

# ending mqtt loop
client.loop_stop(force=False)

# routine to constantly pan the camera horizontally.
# not be the full course of the servo though : if an object appears on the outer edge of the screen
# and the servo is already at its farthest position, we're stuck.

# image is 1000x1000. If something appears at the outer edge, it is about 500px away
# so there needs to be enough rotation left on the device to center the camera on this position.
# as calculated, 1° of rotation moves objects on screen by 26.5px. So 500px = ~18.8°
# servo will pan from 20 to 160°, so we should be good.

import logging
from subprocess import Popen, PIPE
from threading import Thread
from time import sleep
from gpiozero import AngularServo, OutputDevice
from gpiozero.pins.pigpio import PiGPIOFactory
from numpy import arange
import variables

logging.basicConfig(filename='detector.log', filemode='w',
                    format='%(asctime)s %(levelname)s %(message)s', datefmt='%d/%m/%Y %H:%M:%S :', level=logging.DEBUG)

### Start the pigpio daemon on the remote RPI to allow controlling the GPIO pins remotely

if len(Popen(["ssh", f"{variables.user}@{variables.ip}", "ps aux | grep pigpiod | grep -v grep"], stderr=PIPE,
                 stdout=PIPE).communicate()[0]) < 5:
    try:
        Popen(["ssh", f"{variables.user}@{variables.ip}", "sudo pigpiod"])
        sleep(1)
        if len(str(Popen(["ssh", f"{variables.user}@{variables.ip}", "ps aux | grep pigpiod | grep -v grep"], stderr=PIPE,
                         stdout=PIPE).communicate()[0])) == 0:
            logging.critical('Pigpio daemon failed to start on the remote raspberry.\nSystem will *NOT* work. Exiting.')
            variables.exit = True
            exit(1)
    except Exception as e:
        print(str(e))
        logging.critical('Pigpio daemon failed to start on the remote raspberry.\nSystem will *NOT* work. Exiting.')
        variables.exit = True
        exit(1)
### SETUP THE SERVOS ###
factory = PiGPIOFactory(host=variables.ip)
pan_servo = AngularServo(18, min_pulse_width=0.0006, max_pulse_width=0.0024, frame_width=0.02, min_angle=0, max_angle=180,
                         initial_angle=20, pin_factory=factory)
tilt_servo = AngularServo(12, min_pulse_width=0.0006, max_pulse_width=0.0024, frame_width=0.02, min_angle=0, max_angle=180,
                          initial_angle=90, pin_factory=factory)
### SETUP THE VALVE ###
#Note : this is actually a transistor, to control a relay, to control the electrovalve, which is powered by the mains supply.
#the relay is powered by the 5V supply that also powers the servos. 
valve = OutputDevice(23, initial_value=False, pin_factory=factory)
#valve.state = 0
########################

#pan_servo.angle = 20
# sleep(5)
#tilt_servo.angle = 90

class PanCamera(Thread):

    def __init__(self):
        Thread.__init__(self)
        #tilt_servo.angle = 90 # set tilt_servo to default horizontal position

    def run(self):
        while True:
            if not variables.pan_servo_going_right:
                for i in arange(20, 160, 20):
                    if variables.pan_is_running:
                        pan_servo.angle = i
                        variables.pan_servo_position = i
                        #print('angle going right', pan_servo.angle)
                        j = 0
                        while not j == 40:
                            sleep(0.05)
                            if not variables.pan_is_running:
                                exit(0)
                            j += 1
                    else:
                        exit(0)
                variables.pan_servo_going_right = True
            else:
                for i in arange(160, 20, -20):
                    if variables.pan_is_running:
                        pan_servo.angle = i
                        variables.pan_servo_position = i
                        #print('angle going left', pan_servo.angle)
                        j = 0
                        while not j == 40:
                            sleep(0.05)
                            if not variables.pan_is_running:
                                exit(0)
                            j += 1
                    else:
                        exit(0)
                variables.pan_servo_going_right = False

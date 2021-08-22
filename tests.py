
#TODO: get servos and test the library.
from subprocess import Popen
from threading import Thread
from time import sleep
from gpiozero import AngularServo
from gpiozero.pins.pigpio import PiGPIOFactory
import numpy as np
#import variables

factory = PiGPIOFactory(host='192.168.3.46')

pan_servo = AngularServo(13, min_pulse_width=0.1, max_pulse_width=0.5, frame_width=20, min_angle=0, max_angle=180,
                             pin_factory=factory)
tilt_servo = AngularServo(18, min_pulse_width=0.1, max_pulse_width=0.5, frame_width=20, min_angle=0, max_angle=180,
                             pin_factory=factory)

#print(pan_servo.angle)
pan_servo.angle = 90
tilt_servo.angle = 90


"""
class pan(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.factory = PiGPIOFactory(host=variables.ip)

        self.pan_servo = AngularServo(18, min_pulse_width=0.1, max_pulse_width=0.5, frame_width=20, min_angle=0, max_angle=180,
                             pin_factory=self.factory)

    def run(self):
        while True:
            if not variables.servo_going_right:
                print('GOING LEFT')
                for i in np.arange(20, 160, 20):
                    if variables.pan_is_running:
                        self.pan_servo.angle = i
                        variables.servo_position = i
                        #print(self.pan_servo.angle)
                        sleep(1)
                    else:
                        exit(0)
                variables.servo_going_right = True
            else:
                print('GOING RIGHT')
                for i in np.arange(160, 20, -20):
                    if variables.pan_is_running:
                        self.pan_servo.angle = i
                        variables.servo_position = i
                        sleep(1)
                    else:
                        exit(0)
                variables.servo_going_right = False


#pan = pan()
#pan.start()
#print(pan.is_alive())
#sleep(10)
#variables.pan_is_running = False
#sleep(3)
#print(pan.is_alive())

#variables.pan_is_running = True
#pan().start()

"""
"""
while True:
    servo.angle= -90
    print(servo.value)
    sleep(1)
    servo.angle = 90
    print(servo.value)

    sleep(1)



led = LED(24, pin_factory=factory)

running = True

def test():

    #led = LED(26)

    for i in range(5):
        led.off()
        sleep(1)
        led.on()
        sleep(1)



t = Thread(target=test)

t.start()

for i in range(15):
    print(t.is_alive())
    sleep(1)
running = False
for i in range(10):
    print(t.is_alive())
    sleep(1)
"""



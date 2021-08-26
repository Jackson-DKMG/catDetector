# Move the camera and water spray assembly to bring the detected object at the center of the image.
# A fun thing to do would be to calculate a vector from two distinct frames, and target the predicted position of the object.
# Complicated and yolo is essentially crap, so some other time.

### PIGPIO is required on the remote RPI. See installation instructions at https://gpiozero.readthedocs.io/en/stable/remote_gpio.html ###

from threading import Thread
from time import sleep
import scanner
import variables


class Target:
    def __init__(self, x, y):  # pass the coordinates to target.
        # Inform main thread that targeting is in progress
        #print('Start targeting:', time())
        variables.targeting = True
        self.x = x
        self.y = y

    def run(self):

        pan = Thread(target=self.pan(self.x))  # using threads *should* allow to move both servos simultaneously
        pan.start()
        tilt = Thread(target=self.tilt(self.y)) #yes, the thread spawns other threads. Incepthreads.
        tilt.start()

        while pan.is_alive() and tilt.is_alive():
            sleep(0.001)  # wait for the servos to be aligned TODO: this is probably the wrong way to do it.

        # open the electrovalve and spray water
        self.spray()

        sleep(1) #make it faster #sleep(2) # wait a moment before going back to the stream analysis,
        # to avoid targeting again right away, as the servos tends to misbehave.

        # We're done here, let's go back to analysis.
        variables.targeting = False
        exit(0)

    def pan(self, x):
        ### move the horizontal servo
        # 1 degree of rotation moves objects on screen by 23.5 px, it seems.
        # so, between the center pixel 500 and x, eg = 289 :
        # 500 - 289 = 211 --> 211/26.5 = 8.34°. New angle should be current_position + 8.34°, rounded.
        angle = round((500 - x) / 23.5)  # the angle may be negative, so the servo will move either side.
        # TODO: remove below block for production ########
        print('Pan Servo position:', variables.pan_servo_position)
        print('Pan angle:', angle)
        ##################################################
        if abs(angle) < 3: #trying to avoid the servo making constant micro adjustments
            return

        new_angle = round(variables.pan_servo_position + angle)
        if new_angle < 0 or new_angle > 180:
            scanner.pan_servo.angle = 90
            return  # don't try to rotate the servo out of range
        scanner.pan_servo.angle = new_angle
        variables.pan_servo_position = scanner.pan_servo.angle  # store the new position of the servo
        return

    def tilt(self, y):
        # move the vertical servo
        # default position of the servo is 90 (mounted so that 90° is horizontal)
        angle = round((500 - y) / 23.5)  # the angle may be negative, so the servo will move up or down.
        # TODO: remove below block for production ########
        print('Tilt servo position:', variables.tilt_servo_position)
        print('Tilt angle:', angle)
        #################################################
        if abs(angle) < 3: #trying to avoid the servo making constant micro adjustments
            return
        new_angle = round(variables.tilt_servo_position - angle)  #TODO : maybe mount the servo in the right position. Jackass.
        if new_angle < 45 or new_angle > 155:
            scanner.tilt_servo.angle = 90
            return  # probably not useful to aim too low or too high.
        scanner.tilt_servo.angle = new_angle
        variables.tilt_servo_position = scanner.tilt_servo.angle  # store the new position of the servo
        return

    def spray(self):
        # once the targeting is done, open an electrovalve linked to the water hose.
        # one second should be enough. Maybe less and resume scanning/targeting right away, for an 'aggressive' mode.
        #print('Spray:', time())
        return

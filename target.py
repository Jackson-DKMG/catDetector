# Move the camera and water spray assembly to bring the detected object at the center of the image.
# A fun thing to do would be to calculate a vector from two distinct frames, and target the predicted position of the object.
# Complicated and yolo is essentially crap, so some other time.

### PIGPIO is required on the remote RPI. See installation instructions at https://gpiozero.readthedocs.io/en/stable/remote_gpio.html ###

from threading import Thread
from time import sleep
import scanner
import variables
from math import isclose


class Target:
    def __init__(self, x, y):  # pass the coordinates to target.
        # Inform main thread that targeting is in progress
        #print('Start targeting:', time())
        variables.targeting = True
        self.x = x
        self.y = y
        self.pan_done = False
        self.tilt_done = False

    def run(self):

        Thread(target=self.pan, args=(self.x,)).start()
        Thread(target=self.tilt, args=(self.y,)).start()

        while not (self.pan_done and self.tilt_done): #this should ensure that the servos are properly aligned before firing.
            sleep(0.001)

        # open the electrovalve and spray water
        if variables.target_detected == True: #if a target was detected on two subsequent frames. Otherwise, just point a it but don't fire.
            self.spray()
        else:
            variables.target_detected = True #next time the targeting function is called, it will fire.

        sleep(0.25) #make it faster #sleep(2) # wait a moment before going back to the stream analysis,
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
        #print('Pan Servo position:', variables.pan_servo_position)
        #print('Pan angle:', angle)
        ##################################################
        #if abs(angle) < 3: #trying to avoid the servo making constant micro adjustments
        #    return

        new_angle = round(variables.pan_servo_position + angle)
        if new_angle < 0 or new_angle > 180:
            scanner.pan_servo.angle = 90
            return  # don't try to rotate the servo out of range
        scanner.pan_servo.angle = new_angle
        while not isclose(scanner.pan_servo.angle, new_angle, abs_tol=1):
            sleep(0.001)
        variables.pan_servo_position = scanner.pan_servo.angle  # store the new position of the servo
        self.pan_done = True
        return

    def tilt(self, y):
        # move the vertical servo
        # default position of the servo is 90 (mounted so that 90° is horizontal)
        angle = round((500 - y) / 23.5)  # the angle may be negative, so the servo will move up or down.
        # TODO: remove below block for production ########
        #print('Tilt servo position:', variables.tilt_servo_position)
        #print('Tilt angle:', angle)
        #################################################
        #if abs(angle) < 3: #trying to avoid the servo making constant micro adjustments
        #    return
        new_angle = round(variables.tilt_servo_position - angle)  #TODO : maybe mount the servo in the right position. Jackass.
        if new_angle < 30 or new_angle > 135:
            scanner.tilt_servo.angle = 90
            return  # probably not useful to aim too low or too high.
        scanner.tilt_servo.angle = new_angle
        while not isclose(scanner.tilt_servo.angle, new_angle, abs_tol=1):
            sleep(0.001)
        variables.tilt_servo_position = scanner.tilt_servo.angle  # store the new position of the servo
        self.tilt_done = True
        return

    def spray(self):
        # once the targeting is done, open an electrovalve linked to the water hose.
        # one second should be enough. Maybe less and resume scanning/targeting right away, for an 'aggressive' mode.
        #print('Spray:', time())
        scanner.valve.on()
        sleep(0.5)
        scanner.valve.off()
        variables.target_detected = False  #reset that variable
        #sleep(0.5)
        return

import logging
import cv2
import torch
from queue import Queue  # needed to store the camera frames so as to always use the latest one
from threading import Thread  # fill the queue in a background thread
from time import sleep, time
from subprocess import Popen, PIPE
from numpy import argmax
from sys import exit as EXIT
from os import chdir
import target
import variables
import scanner

logging.basicConfig(filename='detector.log', filemode='w',
                    format='%(asctime)s %(levelname)s %(message)s', datefmt='%d/%m/%Y %H:%M:%S :', level=logging.DEBUG)

class Scan:

    def __init__(self):
        # instantiate the model
        chdir('data')
        self.model = torch.hub.load('ultralytics/yolov5', 'yolov5x6', pretrained=True) #already downloaded when building the docker image.
        self.model.conf = 0.70
        #otherwise, going to take some time, it's 269Mo.
        #self.model.eval()
        with open('coco.names', 'rt') as f:
            self.classes = f.read().rstrip('\n').split('\n')
        # set camera resolution.
        self.width = variables.width
        self.height = variables.height
        # SSH user and camera IP
        self.user = variables.user
        self.ip = variables.ip
        self.port = variables.port
        # start pigpio on the rpi
        self.start_pigpio_daemon()
        # create a queue object, acting as a buffer containing only the latest image received from the camera.
        # if reading directly from the OpenCV stream, the oldest frame in the buffer is read, causing delays to accumulate
        self.queue = Queue(maxsize=1)  # only need the latest frame
        # queue thread starting all video streaming and processing.
        self.queue_thread = Thread(target=self.video_stream_to_queue, daemon=True)
        self.stream_thread_is_running = False

    def exit(self):
        variables.exit = True #to let the run() thread know that it should exit too.
        EXIT()

    def start_pigpio_daemon(self):
        """Start the pigpio daemon on the remote RPI to allow controlling the GPIO pins remotely"""
        Popen(["ssh", f"{self.user}@{self.ip}", "sudo pigpiod"])
        sleep(0.5)
        if len(str(Popen(["ssh", f"{self.user}@{self.ip}", "ps aux | grep pigpiod | grep -v grep"], stderr=PIPE,
                         stdout=PIPE).communicate()[0])) == 0:
            logging.critical('Pigpio daemon failed to start on the remote raspberry.\nSystem will *NOT* work. Exiting.')
            self.exit()

    def video_stream_to_queue(self):
        """Start the video capture on the RPI, open the video stream in OpenCV, start the queue
        and use it as a buffer containing the latest frame"""
        Popen(["ssh", f"{self.user}@{self.ip}", "sudo killall raspivid"])  # kill any stray processes
        sleep(1)
        start_raspivid_process = Popen(
            ["ssh", f"{self.user}@{self.ip}", f"raspivid  --codec MJPEG -fps 15 -w {self.width}\
                              -h {self.height} -awb greyworld -n -pf baseline -ih -t 0 -l -o tcp://0.0.0.0:{self.port}"],
            stderr=PIPE,stdout=PIPE)         # 15 fps is enough. # the 'greyworld' option prevents a red tint on the image

        #Let raspivid start (or fail anyway)
        sleep(0.5)
        ### ensure raspivid is running, then kill the start_raspivid_process (after the streaming started - line 100-something)
        timeout = 0
        while not Popen(["ssh", f"{self.user}@{self.ip}", "ps aux | grep raspivid | grep -v grep"], stderr=PIPE,
                      stdout=PIPE).communicate()[0].decode('UTF-8'):
                sleep(0.5)
                timeout += 1
                if timeout == 3:
                    logging.critical('Raspivid failed to start on the remote raspberry.\nSystem will *NOT* work. Exiting.')
                    Popen(["ssh", f"{self.user}@{self.ip}", "sudo killall pigpiod"]) #the pigpio daemon uses CPU permanently.
                    Popen(["ssh", f"{self.user}@{self.ip}", "sudo killall raspivid"]) #just in case
                    sleep(0.5)
                    self.exit()

        sleep(0.5)  # just to let raspivid properly start or something. The below line fails regularly otherwise.

        self.stream = cv2.VideoCapture(f"tcp://{self.ip}:{self.port}")
        # stream is encoded in MJPEG instead of H264: this eliminates the need for OpenCV to decode each frame as it is natively JPEG. I think.
        # either way, it makes the frame processing significantly faster.
        self.stream.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
        # don't need to store many frames in the buffer, as only the most recent is used.
        self.stream.set(cv2.CAP_PROP_BUFFERSIZE, 2)
        ### ensure that the stream object is actually receiving images.
        timeout = 0
        while True:
            (run, _) = self.stream.read()
            if run:
                break
            elif timeout == 4:
                logging.critical("Streaming isn't working.\nSystem will *NOT* work. Exiting.")
                Popen(["ssh", f"{self.user}@{self.ip}", "sudo killall raspivid"])
                Popen(["ssh", f"{self.user}@{self.ip}", "sudo killall pigpiod"])
                sleep(0.5)
                self.exit()
            sleep(0.5)
            timeout += 1
        start_raspivid_process.terminate()  # once the stream is running, we can kill the process
        start_raspivid_process.wait()
        self.stream_thread_is_running = True

        ### Now populate the Queue object with the latest stream frame.
        while self.stream_thread_is_running:
            try:
                (_, img) = self.stream.read()
                if not self.queue.empty():
                    self.queue.get_nowait()
                self.queue.put(img)
            except:
                pass
            sleep(0.01)  # 15 fps = 1/15. To test further, but that way it should be synced with the frames coming in and save some CPU.
            # update : not really. Framerate is nearly halved whatever the original camera fps. Still, 15 fps is fine.
            # update 2 : now the framerate remains nearly identical to the original one (14.97 FPS on the processed frames)
        # The 'stream_thread_is_running' flag allows the run function to wait until the stream is running and the queue populated.

    def run(self):
        """Main function. Pass the video frames through YOLO V4, searching for living things from the COCO classes,
        except persons. """

        ###start the queue
        self.queue_thread.start()

        while not self.stream_thread_is_running:
            sleep(0.25)
            if variables.exit:
                self.exit()

        ### start the pan routine
        scanner.PanCamera().start()

        #TODO: remove below block for production ########
        font = cv2.QT_FONT_NORMAL
        starting_time = time()  # time + frame number to calculate the FPS.
        frame_id = 0
        ######################################

        variables.analysis_is_running = True

        # count frames before resuming the pan routine after targeting an object.
        resume_pan_timeout = 0

        while True:  # Main loop, won't exit until the program is killed.
            frame = self.queue.get()  # always process the latest image received from the camera.
            #TODO: remove below block for production ########
            frame_id += 1
            ######################################
            if variables.analysis_is_running:
                try:
                    ### run each frame through the model.
                    results = self.model(frame) #a tensor with all the detected objects as arrays (coords, class)
                    ###filter the objects pertaining to the relevant COCO classes (living stuff) and select the target with highest confidence
                    #TODO: remove class 0 ('person') for production
                    #print(results.xywh[0])
                    targets = [i for i in results.xywh[0]if i[5] in [0, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]]

                    #If nothing is detected, the above gives an empty list. No exception is raised.
                    if targets:
                        main_target = targets[0] #results are already ordered by decreasing confidence. Index 0 is always the right one
                        #print(self.classes[int(main_target[5].item())], str(round(main_target[4].item(), 2)))
                        #get center coordinates
                        x,y = round(main_target[0].item()), round(main_target[1].item())

                        if variables.preview == 'on': #below block not executed if the live video isn't displayed
                            cv2.putText(frame, self.classes[int(main_target[5].item())] + " " + str(round(main_target[4].item(), 2)),
                                        (x,y + 30), font, 2, (0, 255, 0), 3)
                            # display a dot at the center of the detected object.
                            cv2.circle(frame, (x,y), radius=5, color=(0, 0, 255), thickness=-1)
                            ######################################
                        variables.pan_is_running = False  # stop the pan routine and break the analysis loop,
                        variables.analysis_is_running = False  # as something was detected.
                        resume_pan_timeout = 0 # if the value started increasing after the previous targeting, reset it.
                        ### start the targeting function.
                        variables.tilt_servo_position = scanner.tilt_servo.angle
                        variables.pan_servo_position = scanner.pan_servo.angle
                        Thread(target=target.Target(x,y).run).start()
                        #break  # can't target multiple objects at once, so.

                    else:
                        variables.target_detected = False

                except KeyboardInterrupt:
                    break

                except Exception as e:  # whatever the exception may be. Just log it and try to continue the program.
                    logging.critical(f"Error: {str(e)}")
                    pass

            # pan routine was stopped when detecting a target. Resume it after a few frames being analyzed at the
            # same location, as the previous object might still be there.
                if not variables.pan_is_running:
                    resume_pan_timeout += 1
                    if resume_pan_timeout == 20:  # this is less than 2 seconds, normally.
                        resume_pan_timeout = 0
                        variables.pan_is_running = True
                        scanner.PanCamera().start()
            else:
                # analysis was stopped because a target was detected. If the targeting is done, resume analysis.
                sleep(0.05) # need more reactivity #sleep(0.25)
                if not variables.targeting:
                    variables.analysis_is_running = True

            if variables.preview == 'on':
                elapsed_time = time() - starting_time
                fps = frame_id / elapsed_time
                cv2.putText(frame, "FPS: " + str(round(fps, 2)), (10, 50), font, 2, (0, 0, 0), 3)
                cv2.imshow("Image", frame)  # display the video stream and detected objects.

                key = cv2.waitKey(1)
                if key == 27:
                    break

        self.stream_thread_is_running = False
        variables.pan_is_running = False
        variables.analysis_is_running = False
        scanner.valve.off()
        scanner.pan_servo.angle = 90
        scanner.tilt_servo.angle = 90
        self.stream.release()
        if variables.preview == 'on':
            cv2.destroyAllWindows()
        Popen(["ssh", f"{self.user}@{self.ip}", "sudo killall pigpiod"])
        sleep(0.5)

        self.exit()
        ########################################################

if __name__ == '__main__':
    Scan().run()

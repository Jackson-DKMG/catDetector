import logging
import cv2
from queue import Queue  # needed to store the camera frames so as to always use the latest one
from threading import Thread  # fill the queue in a background thread
from time import sleep, time
from subprocess import Popen, PIPE
from numpy import argmax
from sys import exit as EXIT
import target
import variables



import scanner

logging.basicConfig(filename='detector.log', filemode='w',
                    format='%(asctime)s %(levelname)s %(message)s', datefmt='%d/%m/%Y %H:%M:%S :', level=logging.DEBUG)

class Scan:

    def __init__(self):
        # instantiate the model
        self.model = cv2.dnn.readNet('data/yolov4.weights', 'data/yolov4.cfg')
        #TODO: remove below block for production ########
        # just to get names for detected objects.
        with open('data/coco.names', 'rt') as f:
            self.classes = f.read().rstrip('\n').split('\n')
        ######################################
        # use the gpu
        self.model.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
        self.model.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA_FP16)
        # set camera resolution # square, otherwise the image is resized and the shapes would be flattened, probably affecting the detection rate.
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
            ["ssh", f"{self.user}@{self.ip}", f"raspivid  --codec MJPEG -fps 30 -w {self.width}\
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
                    blob = cv2.dnn.blobFromImage(frame, 1 / 255, (320, 320), (0, 0, 0), swapRB=True, crop=False)
                    self.model.setInput(blob)
                    output_layers = self.model.getUnconnectedOutLayersNames()
                    layer_output = self.model.forward(output_layers)

                    classes_id = []  # store the detected classes
                    confidences = []  # store the corresponding confidence levels
                    boxes = []  # store the bounding boxes coordinates

                    for output in layer_output:
                        for detection in output:
                            score = detection[5:]
                            confidence = float(score[argmax(score)])
                            if argmax(score) in [0, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24]:
                                # animals from the COCO classes. #TODO: remove 0 (=person) for production
                                if confidence > 0.45:
                                    classes_id.append(argmax(score))
                                    confidences.append(confidence)
                                    center_x = int(detection[0] * self.width)
                                    center_y = int(detection[1] * self.height)
                                    w = int(detection[2] * self.width)
                                    h = int(detection[3] * self.height)
                                    # Rectangle coordinates
                                    x = int(center_x - w / 2)
                                    y = int(center_y - h / 2)
                                    boxes.append([x, y, w, h])

                    for _ in range(len(classes_id)):
                        if variables.analysis_is_running:  # this should avoid the target thread being fired up multiple times.
                            indices = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0)
                            ### nmsthreshold at 0 so that all overlapping boxes are merged into one.
                            first_index = indices[0][0]
                            # indices may be an empty tuple. Not sure why, the NMS fails somehow ? Exception is caught below.

                            ### coordinates of the center of the box. This will be the target.
                            x = int(boxes[first_index][0] + boxes[first_index][2] / 2)
                            y = int(boxes[first_index][1] + boxes[first_index][3] / 2)

                            #TODO: remove below block for production ########
                            #print(f'Detected {self.classes[classes_id[first_index]]} {str(round(confidences[first_index], 2))}, {time()}')
                            cv2.putText(frame, self.classes[classes_id[first_index]] + " " + str(
                                round(confidences[first_index], 2)),
                                        (x, y + 30), font, 2, (0, 255, 0), 3)
                            # display a dot at the center of the detected object.
                            cv2.circle(frame, (x, y), radius=5, color=(0, 255, 0), thickness=-1)
                            ######################################
                            variables.pan_is_running = False  # stop the pan routine and break the analysis loop,
                            variables.analysis_is_running = False  # as something was detected.
                            resume_pan_timeout = 0 # if the value started increasing after the previous targeting, reset it.
                            ### start the targeting function.
                            Thread(target=target.Target(x, y).run).start()
                            break  # can't target multiple objects at once, so.
                        else:
                            break  # targeting in progress, break out of the loop

                except IndexError:  # when the indices variable is an empty tuple.
                    pass

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


        #TODO: remove below block for production ########
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
        self.stream.release()
        cv2.destroyAllWindows()
        Popen(["ssh", f"{self.user}@{self.ip}", "sudo killall pigpiod"])
        sleep(0.5)

        self.exit()
        ########################################################


if __name__ == '__main__':
    Scan().run()

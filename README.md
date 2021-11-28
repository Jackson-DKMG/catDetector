**WORK IN PROGRESS**

An animal detector and repellent, using a camera mounted on a Raspberry Pi and a couple servos.
<br><br>
Video stream is analyzed in real time by a laptop (for now) with a CUDA-capable device running a YOLO V4 model.
(The RPi has nowhere near enough processing power to handle this task - getting about 0.35 FPS. Maybe with a Coral TPU ?
The final objective is to make a completely independent system.)<br>
The pan servo continuously scans a perimeter of about 140° (it has a course of 180°, so if something is detected on the edge of the image it can still target it.<br>
When an object pertaining to the list of foes is detected (currently : all living creatures from the COCO dataset), the servos bring it to the center of the image, and an electrovalve is activated for 0.5s.<br>
The valve is connected to the water hose, and a to a small diameter pipe fitted on the camera.<br>
To handle the pressure, the valve is a 220V model, powered on the mains supply and controlled by the RPi with a relay and a transistor.<br>
<br>
The servos are also powered externally and only controlled by the RPi.
<br><br>
A wiring diagram is provided (yes, made with Paint).
<br>

**REQUIREMENTS**

A few specific Python packages for controlling the GPIO pins on the Raspberry Pi, nothing too fancy: gpiozero & pigpio, numpy, OpenCV.
<br><br>
And pigpio must be installed on the RPi. Program attempts to start the pigpio daemon (pigpiod). Servos won't work without it.<br>
The GPIO pins must also be set available over the network.<br>
Run with <code>python3 main.py USER IP PORT --preview on/off</code> (<code>preview</code> is optional and default to off. If off, the live video isn't displayed)
<br><br>
<u>However</u> : OpenCV has to be built with CUDA support otherwise the framerate will drop to ~5-7 FPS on a Ryzen 4900 with 16 cores, so...<br> 
This being pretty painful, I'm running the program in a docker container, see details below.
<br>

**NOTE**

The YOLO weights are not included here (400 Mo+). They can be downloaded from Darknet's github.<br>
The version I'm using is https://github.com/AlexeyAB/darknet/releases/download/darknet_yolo_v4_pre/yolov4-p6.weights, but there are others, lighter ones at https://github.com/AlexeyAB/darknet/releases. 

**DOCKERFILE**

It's easier to run the program inside a docker container, built with a Cuda-capable OpenCV. The image is pretty heavy essentially because of the cuda & cudnn libraries.<br>
Anyway, it's also a base for building other Deep Learning/Machine Learning images.<br>
The dockerfile installs all the dependencies. In the same folder, there must be :<br>
    -the libcudnn .deb packages (to download from https://developer.nvidia.com/rdp/cudnn-download). They're the following:<br>
        cuDNN Runtime Library for Ubuntu20.04 x86_64 (Deb)<br>
        cuDNN Developer Library for Ubuntu20.04 x86_64 (Deb)<br>
    -a ssh folder containing an id_rsa and known_hosts for ssh'ing into the RPi without a prompt.<br>
    -the folder with all the program files

The dockerfile ARG variables should be modified as necessary. 

If using Docker, the container can be run as follows (to display the video on the host):<br>
<code>xhost + && docker run --name=catDetector --gpus all --rm -it --net=host --ipc=host -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix cat_detector:v3 python3 main.py USER IP PORT --preview on/off (default off)</code>

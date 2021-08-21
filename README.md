**WORK IN PROGRESS**

An animal detector, using a camera mounted on a Raspberry Pi and a couple servos.

Video stream is analyzed in real time by a laptop (for now) with a CUDA-capable device running a YOLO V4 model.
The RPi has nowhere near enough processing power to handle this task - getting about 0.35 FPS. Maybe with a Coral TPU ?
The final objective is to make a completely independent system.

When an object is detected, the servos bring it to the center of the image. 

A water spray will be added later on, in an attempt to make these animals flee and (especially the cats) stop using my yard as their goddamn toilet. Seriously.


**REQUIREMENTS**

A few specific Python packages for controlling the GPIO pins on the Raspberry Pi, nothing too fancy: gpiozero, numpy, OpenCV.

<u>However</u> : OpenCV has to be built with CUDA support otherwise the framerate will drop to ~5-7 FPS on a Ryzen 4900 with 16 cores, so... 
This being pretty painful, I'm running the program in a docker container, with an image based on datamachines/cudnn_tensorflow_opencv (which is quite heavy with 11+ Go, it's possible to remove a lot of the stuff installed by default in the Dockerfile before building to keep the size minimal -- still over 8 Go due to the CUDA libs).

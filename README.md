**WORK IN PROGRESS**

An animal detector, using a camera mounted on a Raspberry Pi and a couple servos.

Video stream is analyzed in real time by a laptop (for now) with a CUDA-capable device running a YOLO V4 model.
The RPi has nowhere near enough processing power to handle this task - getting about 0.35 FPS. Maybe with a Coral TPU ?
The final objective is to make a completely independent system.

When an object is detected, the servos bring it to the center of the image. 

A water spray will be added later on, in an attempt to make these animals flee and (especially the cats) stop using my yard as their goddamn toilet. Seriously.

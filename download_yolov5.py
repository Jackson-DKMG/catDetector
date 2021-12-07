import torch
from os import chdir
chdir('data')
torch.hub.load('ultralytics/yolov5', 'yolov5x6', pretrained=True)
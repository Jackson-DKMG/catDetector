from super_gradients.training import models
from super_gradients.common.object_names import Models
from os import chdir
chdir('/catDetector/data')
models.get(Models.YOLO_NAS_M, pretrained_weights="coco")
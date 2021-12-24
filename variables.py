from argparse import ArgumentParser
parser = ArgumentParser()
parser.add_argument('user', help='Usage: python3 main.py username ip port --preview on/off (default off)')
parser.add_argument('ip', help='Usage: python3 main.py username ip port --preview on/off (default off)')
parser.add_argument('port', help='Usage: python3 main.py username ip port --preview on/off (default off)')
parser.add_argument('--preview', help='Usage: python3 main.py username ip port --preview on/off (default off)', default='off')

args = parser.parse_args()


analysis_is_running = False
pan_is_running = True
target_detected = False #switch to True if a target is detected, only then activate the water spray. Avoid false positives.
targeting = False
pan_servo_position = 40 #initial pan servo position
tilt_servo_position = 90 #default tilt servo position (horizontal)
pan_servo_going_right = False #servo is going left, or right if False
exit = False
#satellite pi variables
user = args.user
ip = args.ip
port = args.port
preview = args.preview #enable the live video display. Disabled by default.
width = 1000
height = 1000


from argparse import ArgumentParser
parser = ArgumentParser()
parser.add_argument('user', help='Usage: python3 main.py username ip port')
parser.add_argument('ip', help='Usage: python3 main.py username ip port')
parser.add_argument('port', help='Usage: python3 main.py username ip port')
args = parser.parse_args()


analysis_is_running = False
pan_is_running = True
targeting = False
pan_servo_position = 0 #initial pan servo position
tilt_servo_position = 90 #default tilt servo position (horizontal)
pan_servo_going_right = False #servo is going left, or right if False
exit = False
#satellite pi variables
user = args.user
ip = args.ip
port = args.port
width = 1000
height = 1000


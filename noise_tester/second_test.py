import spd3303x
import numpy as np
import cv2
import os
from zaber_drive import axis
import numpy as np

class powersupply:
    def __init__(self):
        self.ps_comm = spd3303x.USBDevice()
        self.ps = self.ps_comm.__enter__()
    def close(self):
        self.ps.__exit__()
    def set_channel(self, voltage, current=0.04, state=True, string='CH1'):
        getattr(self.ps, string).set_voltage(voltage)
        getattr(self.ps, string).set_current(current)
        getattr(self.ps, string).set_output(state)
    def get_voltage(self, string='CH1'):
        return getattr(self.ps, string).get_voltage()
    def set_voltage(self, voltage):
        if voltage > 16:
            voltage = 16
        self.set_channel(voltage)
    def run(self):
        try:
            pass # something
        finally:
            self.close()

ps = powersupply()
a = axis()
a.set_speed(10)

nominal = 117 #117
bounds = 7
increment = 0.01

focus_to_distance_lookup = {
    350: 30,
    400: 70,
    500: 120,
    600: 150,
    700: 160,
    800: 170
}

distance_to_position_lookup = {
    30: [771, 1222, 20, 40], # y (out of 1744) x (2328) height length
    70: [750, 1227, 20, 40],
    120: [695, 1239, 20, 40],
    150: [579, 1262, 20, 40],
    160: [491, 1263, 20, 40],
    170: [380, 1276, 20, 40],
}

x = np.array([i for i in focus_to_distance_lookup.keys()])
y = np.array([focus_to_distance_lookup[i] for i in focus_to_distance_lookup.keys()])
z = np.poly1d(np.polyfit(x, y, 2))

x1 = np.array([i for i in distance_to_position_lookup.keys()])
y1 = np.array([distance_to_position_lookup[i][0] for i in distance_to_position_lookup.keys()])
y2 = np.array([distance_to_position_lookup[i][1] for i in distance_to_position_lookup.keys()])
y3 = np.array([distance_to_position_lookup[i][2] for i in distance_to_position_lookup.keys()])
y4 = np.array([distance_to_position_lookup[i][3] for i in distance_to_position_lookup.keys()])

z1 = np.poly1d(np.polyfit(x1, y1, 1))
z2 = np.poly1d(np.polyfit(x1, y2, 1))
z3 = np.poly1d(np.polyfit(x1, y3, 1))
z4 = np.poly1d(np.polyfit(x1, y4, 1))

os.system('sudo v4l2-ctl -c gain=11000000')
for i, focus_value in enumerate(focus_to_distance_lookup.keys()):
    filename = 'test_data/focus_{:05d}.png'.format(focus_value)
    distance = int(focus_to_distance_lookup[focus_value])
    a.move_to(distance, False)
    # height = int(z3(distance))
    # length = int(z4(distance))
    # starting_position = [int(z1(distance)), int(z2(distance))]
    data = distance_to_position_lookup[focus_to_distance_lookup[focus_value]]
    print(data)
    height = int(data[2])
    length = int(data[3])
    starting_position = [int(data[0]), int(data[1])]
    print(focus_value, distance, starting_position, height, length)
    os.system('sudo python3 serdes.py set_focus:{}'.format(focus_value))
    while True:
        os.system('ffmpeg -y -i tcp://127.0.0.1:5558 -f image2 -vframes 1 {}'.format(filename))
        img = cv2.imread(filename)
        margin_for_image = 100
        rect = img[starting_position[0]:starting_position[0]+height, starting_position[1]:starting_position[1]+length,:]
        rect2 = img[starting_position[0]-margin_for_image:starting_position[0]+height+margin_for_image, starting_position[1]-margin_for_image:starting_position[1]+length+margin_for_image,:]
        cv2.imwrite('{}_0.png'.format(filename[:-4]), rect)
        cv2.imwrite('{}_1.png'.format(filename[:-4]), rect2)
        output_value = np.average(rect)
        if output_value > nominal + bounds:
            ps.set_voltage(float(ps.get_voltage()) - increment)
            continue
        if output_value < nominal - bounds:
            ps.set_voltage(float(ps.get_voltage()) + increment)
            continue
        # image is good
        break

from zaber_motion import Library
from zaber_motion.ascii import Connection
from zaber_motion import Units
from zaber_motion.ascii import AxisSettings

import glob
import sys
import numpy as np
# Library.toggle_device_db_store(True)

PORT = '/dev/ttyUSB0'

test_ports = glob.glob('/dev/tty.usbserial*')
if len(test_ports) > 0:
	PORT = test_ports[0]

class axis:
	def __init__(self, ax=None, scale=3149606):
		if ax is None:
			connection = Connection.open_serial_port(PORT)
			device_list = connection.detect_devices()
			ax = device_list[0].get_axis(1)
		self.ax = ax
		self.scale = scale
	def move_to(self, distance, _async=True):
		self.ax.move_absolute(distance, Units.LENGTH_MILLIMETRES, wait_until_idle=False)
		if not _async:
			self.wait_until_finished()
	def wait_until_finished(self):
		self.ax.wait_until_idle()
	def home(self, _async=True):
		self.ax.home(wait_until_idle=False)
		if not _async:
			self.wait_until_finished()
	def speed(self):
		speed = self.ax.settings.get("maxspeed", Units.VELOCITY_MILLIMETRES_PER_SECOND)
		return speed
	def set_speed(self, speed):
		self.ax.settings.set("maxspeed", speed, Units.VELOCITY_MILLIMETRES_PER_SECOND)
	def get_pos(self):
		return self.ax.get_position()/self.scale*150
	def get_max(self):
		return self.ax.settings.get("limit.max", Units.LENGTH_MILLIMETRES)
	def get_min(self):
		return self.ax.settings.get("limit.min", Units.LENGTH_MILLIMETRES)
	def get_current_location(self):
		return self.ax.get_position(Units.LENGTH_MILLIMETRES)
class gauntry:
	def __init__(self, _async=False):
		connection = Connection.open_serial_port(PORT)
		device_list = connection.detect_devices()
		self.x = axis(device_list[0].get_axis(1), 1209448)
		self.y = axis(device_list[1].get_axis(1), 1209448)
		self.z = axis(device_list[2].get_axis(1), 1209448)
		self.home(_async=_async)
	def move_to(self, x, y, z, _async=False):
		self.x.move_to(x)
		self.y.move_to(y)
		self.z.move_to(z)
		if not _async:
			self.wait_until_finished()
	def home(self, _async=False):
		self.x.home()
		self.y.home()
		self.z.home()
		if not _async:
			self.wait_until_finished()
	def wait_until_finished(self):
		self.x.wait_until_finished()
		self.y.wait_until_finished()
		self.z.wait_until_finished()
	def move(self, z, y, x):
		self.z.move_to(z)
		self.y.move_to(y)
		self.x.move_to(x)


# g = gauntry()
if __name__ == '__main__':
	a = axis()
	a.set_speed(10)
	# a.home()
	# a.wait_until_finished()
	a.move_to(150)
	print("start")
	input()
	offset = 15
	distances = [i for i in range(5,146,5)]
	print(distances)
	for dis in distances:
		print(150 - dis)
		a.move_to(150 - dis, _async=False)
		input()


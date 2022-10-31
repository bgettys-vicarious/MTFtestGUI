from zaber_drive import gauntry
from zaber_motion import Library
Library.enable_device_db_store()
xyz = gauntry()
#xyz.home()
min_y = xyz.y.get_min()
length_y = xyz.y.get_max() - min_y
dist_y = length_y/2
xyz.y.move_to(min_y + dist_y)
xyz.x.move_to(xyz.x.get_max() -40)
## at 25, distance is 38.7 = gets us 13.7

#offset is 13.8mm
xyz.z.move_to(xyz.z.get_max())

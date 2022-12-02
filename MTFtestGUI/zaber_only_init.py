from zaber_drive import gauntry
from zaber_motion import Library
Library.enable_device_db_store()
class Dummy:
    def __init__(self):
        self.xyz_stage = gauntry()

        #a = xyz.y.get_current_location()
        #min_y = xyz.y.get_min()
        #length_y = xyz.y.get_max() - min_y
        #dist_y = length_y/2
       # xyz.y.move_to(min_y + dist_y)
        #xyz.x.move_to(xyz.x.get_max() -80)
        ## at 25, distance is 38.7 = gets us 13.7

        #offset is 13.8mm
        #xyz.z.move_to(xyz.z.get_max())

im_stage_obj = Dummy()
xyz = im_stage_obj.xyz_stage
# max_z = xyz.z.get_max()
# xyz.z.move_to(max_z)
# current_z = xyz.z.get_current_location()
# print(current_z)
xyz.z.move_to(xyz.z.get_max()*.3)
xyz.x.move_to(xyz.x.get_max()-50)
xyz.y.move_to(xyz.y.get_max()*.15)
#xyz.y.move_to(int())


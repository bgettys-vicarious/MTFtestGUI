# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
#this version does not include automated camera bring up - it will work if eyeboth is functional
import os
import time
import cv2
import paramiko
import numpy as np
from zaber_drive import gauntry
import PySimpleGUI as sg
from datetime import datetime
from zaber_motion import Library
import pandas as pd
import json
import threading

# note for first run on new computer: RUN ZABER LAUNCHER FIRST OR YOU WILL GET WIERDO ERRORS
# make sure zaber has a database
Library.enable_device_db_store()
# fixme, eventually I need to change this to the second offline method explained HERE:
# https://www.zaber.com/software/docs/motion-library/ascii/howtos/device_db/

#READ THE FOCUS TABLE
# this is code taken from camera_controller.py


class ImageArea:
    def __init__(self, near, focal, far):
        self.near = float(near)
        self.focal = float(focal)
        self.far = float(far)

class PositionOverlay:
    def __init__(self, input_img, counter):
        self.image = input_img
        if counter == 0: #ensures this happens only on the first frame for speed
            self.CalculateOverlay()
        else:
            pass

    def CalculateOverlay(self):
        # #calculate the grid overlay in real time (this assumes side-by-side images)
        self.height = self.image.shape[0]
        self.center_height = .5 * self.height
        self.seventy_on_center_height = .7*self.center_height
        self.top_line_height= self.center_height - self.seventy_on_center_height
        self.bottom_line_height = self.center_height + self.seventy_on_center_height

        self.width = self.image.shape[1]
        self.one_side_width = .5*self.width
        self.center_one_side_width = .5*self.one_side_width
        self.seventy_on_center_width = .7*self.center_one_side_width
        self.left_img_left_side_width = self.center_one_side_width - self.seventy_on_center_width
        self.left_img_right_side_width = self.center_one_side_width + self.seventy_on_center_width
        self.right_img_left_side_width = self.one_side_width + self.center_one_side_width - self.seventy_on_center_width  #offset to account for second image
        self.right_img_right_side_width = self.one_side_width + self.center_one_side_width + self.seventy_on_center_width

    def AddOverlay(self):
        top_horiz_line = cv2.line(self.image, (0, int(self.top_line_height)), (int(self.width),int(self.top_line_height)), (255, 0, 0), 1)
        bottom_horiz_line =  cv2.line(self.image, (0, int(self.bottom_line_height)), (int(self.width),int(self.bottom_line_height)), (255, 0, 0), 1)

        left_img_left_line = cv2.line(self.image, ( int(self.left_img_left_side_width), 0), (int(self.left_img_left_side_width),int(self.height)), (255, 0, 0), 1)
        left_img_right_line = cv2.line(self.image, ( int(self.left_img_right_side_width), 0), (int(self.left_img_right_side_width),int(self.height)), (255, 0, 0), 1)
        left_img_left_line = cv2.line(self.image, ( int(self.right_img_left_side_width), 0), (int(self.right_img_left_side_width),int(self.height)), (255, 0, 0), 1)
        left_img_right_line = cv2.line(self.image, ( int(self.right_img_right_side_width), 0), (int(self.right_img_right_side_width),int(self.height)), (255, 0, 0), 1)

        center_horiz =  cv2.line(self.image, (0, int(self.center_height)), (int(self.width),int(self.center_height)), (0, 0, 255), 1)
        center_vert_left =  cv2.line(self.image, ( int(self.center_one_side_width), 0), (int(self.center_one_side_width),int(self.height)), ( 0, 0, 255), 1)
        center_vert_right = cv2.line(self.image, ( int(self.center_one_side_width + self.one_side_width), 0), (int(self.center_one_side_width + self.one_side_width),int(self.height)), ( 0, 0, 255), 1)



def excel_read_config(loc_config):
    df = pd.read_excel(loc_config, usecols=[1])  # this is a data frame object
    # note: first ROW is Vera number and is not used! it starts counting from the first int in row 2, which is #0 in this data structure
    address = str(df.values[0])
    address = address[2:-2] #we do this to get rid of the [' '] from np array
    print(address)
    serdes_home = str(df.values[1])
    serdes_home = serdes_home [2:-2]
    input_focus_one = float(df.values[2])
    input_stage_one_near = float(df.values[3])
    input_stage_one_far = float(df.values[4])
    num_picts = float(df.values[8])
    CloseArea = ImageArea(input_stage_one_near, input_focus_one, input_stage_one_far)
    #FarArea = ImageArea(input_stage_two_near, input_focus_two, input_stage_two_far)
    AreaList = [CloseArea, ] # FarArea]
    return address, serdes_home, AreaList, num_picts

class FocusStuff:
    def __init__(self, SSH_session, filepath, where_serdes):
        self.table_path = filepath
        self.table_data = self.focus_json_to_coords(self.read_focus_json(filepath))
        self.SSH = SSH_session
        self.serdes_path = where_serdes

    def read_focus_json(self, filepath):
        with open(filepath, "r") as f:
            j = json.load(f)
            self.focus_table = self.focus_json_to_coords(j)
        return j

    def focus_json_to_coords(self, curve_json):
       # curve_json = {"focus_lookup": curve_json}
        distance = np.array(
            [int(float(dist)) for dist in sorted(curve_json["focus_lookup"].keys())], #sorted(curve_json["focus_lookup"].keys())], #note, this assumes dict w/in dict called "focus_table"
            dtype=float,
        )

        focuses = []
        for sensor in ["left", "right"]:
            focus_l = np.array(
                [
                    curve_json["focus_lookup"][dist][sensor]
                    for dist in sorted(curve_json["focus_lookup"].keys())
                ],
                dtype=float,
            )
            focuses.append(focus_l)

        coords = list(zip(distance, focuses[0], focuses[1]))
        return coords

    def find_focus(self, x_distance):
    #heavily edited from the example here:
    #https: // github.com / bgettys - vicarious / RoboticDrive / blob / master / support / robotic_drive / camera / focus.py
    #probs not as efficient, but easier to read and debug

        coord_array= np.array(self.table_data,  dtype=float) #cast to array
        all_dist = coord_array[:, 0] # slice for the first column (dist)
        l_focus = coord_array[:,1] # slice for second column (l focus)
        r_focus = coord_array[:,2] # slice for third column (r focus)
        i = 0
        for sensor in [l_focus, r_focus]:
            coeff = np.polyfit(all_dist, sensor, 3 )  # create polynomial fit to focus data for low order
            fit = np.poly1d(coeff) #make a function
            focus_command = fit(x_distance) # get command
            if i == 0:
                left_focus_command = focus_command
            if i ==1 :
                right_focus_command = focus_command
            i = i + 1
        return [left_focus_command, right_focus_command]

    def set_focus(self, x_distance, serdes_path): #maybe don't need serdes path here
        # get values and set variables elegantly for readable/refactorable code
        focus_values = self.find_focus(int(x_distance)) # bercause this is in mm
        focus_value_left = int(focus_values[0])
        focus_value_right = int(focus_values[1])
        command_to_send = 'sudo python3 ' + self.serdes_path + ' set_focus:{},{}'.format(focus_value_left, focus_value_right)
        print(command_to_send)
        ssh_stdin, ssh_stdout, ssh_stderr = self.SSH.exec_command(command_to_send)
        output = ssh_stdout.read()
        if 'with args' in str(output):
            pass
            #print("yay")
        else:
            #print("nay")
            raise Exception("something went wrong. Xavier says:" + (str(output)))

class ImagesAndStage:
    # feed me LIST of each location you'd like to take a picture at FOR A GIVEN FOCAL plane (near limit, focal plane, far limit)
    def __init__(self, test_title, save_to, where_network, AreaList, SSH_session, num_picts, focus_path, where_serdes):
        # gauntry initialization
        self.xyz_stage = gauntry()
        #removing to make testing faster - needs to go back in
        self.xyz_stage.home()
        # set up with y centered (for now - eventually, do something differe)
        min_y = self.xyz_stage.y.get_min()
        length_y = self.xyz_stage.y.get_max() - min_y
        dist_y = length_y/2
        self.xyz_stage.y.move_to(min_y + dist_y)
        # # set up at arbitrary height (100mm)
        self.xyz_stage.z.move_to(self.xyz_stage.z.get_max())
        # networking support
        self.title = test_title
        self.save_loc = str(save_to)
        self.areas = AreaList
        self.repeats = num_picts
        self.SSH_session = SSH_session
        self.tcp = "tcp://" + where_network + ":5558"
        self.focus = FocusStuff(SSH_session, focus_path, where_serdes)
        # GO take our pictures
        #self.capture()

    def save_image(self, current_focal_distance, current_location):
        # makes a file name using the test title & a timestamp
        dateTimeObj = datetime.now()
        string_focal_distance = str(current_focal_distance)
        string_location = str(current_location)
        file_name_current_time =  ('MTF_' + str(self.title) + '_' + dateTimeObj.strftime("%d-%b-%Y-%H-%M-%S") +
         '_distance_' +"_focused_on_" + string_focal_distance + "_stage_loc_" + string_location + '.png')
        # generate an intelligible file name

        command_cap = "ffmpeg -y -i " + self.tcp + " -f image2 -frames:v 1 " + self.save_loc + "/" + file_name_current_time
        print(self.save_loc)
        os.system(command_cap)
        return file_name_current_time

    def move_stage(self, x_distance):
        #print('moving to' + str(x_distance))
        self.xyz_stage.x.move_to(self.xyz_stage.x.get_max() - (x_distance))  # move x axis to where it needs to be



    # overall motion/image capture behavior for the class
    def capture(self):
        sleep_time = float (.3)
        for each_area in self.areas:
            # on plane
            print("about to move to focal plane:" + str(each_area.focal))
            self.move_stage(each_area.focal)
            self.focus.set_focus(each_area.focal, self.focus.serdes_path) # used to be self.focus.serdes_path)
            time.sleep(10)
            print("saving image while focused on plane")
            for n in range(int(self.repeats)):  # take this number of images
                self.save_image(each_area.focal,each_area.focal)
                time.sleep(sleep_time)  # wait .3 between captures)
            print("all images for this location saved")
            time.sleep(sleep_time)
            time.sleep(10)
            # near
            print("about to move to near location:" + str(each_area.near))
            self.move_stage(each_area.near)
            time.sleep(3)
            print("saving image")
            for n in range(int(self.repeats)):  # take this number of images
                self.save_image(each_area.focal, each_area.near)
                time.sleep(sleep_time)  # wait .3 between captures)
            print("all images for this location saved")
            time.sleep(sleep_time)
            # far
            print("about to move to far location:" + str(each_area.far))
            time.sleep(10)
            self.move_stage(each_area.far)
            time.sleep(3)
            print("saving image")
            for n in range(int(self.repeats)):  # take this number of images
                self.save_image(each_area.focal, each_area.far)
                time.sleep(sleep_time)  # wait .3 between captures)
            print("all images for this location saved")
            time.sleep(sleep_time)
        print("done saving")

# play video, open SSH if needed
class View:
    def __init__(self, test_window, network_loc):
        self.address = network_loc
        self.window = test_window


    def Play(self):
        # error handling https://www.geeksforgeeks.org/python-play-a-video-using-opencv/
        address_stream = 'tcp://' + self.address + ':5558'  # no slashes in your input or else this will error #fixme needs error handling
        vid = cv2.VideoCapture(address_stream)
        counter = 0
        while (vid.isOpened()):
            ret, frame = vid.read()
            #handle no frames
            if not ret:
                break

            ## downscale and add image
            frame = cv2.resize(frame, (2048, 872))  # downscale ahead of time
            if counter == 0:
                overlay_obj = PositionOverlay(frame, counter)
            else:
                overlay_obj.image = frame
            overlay_obj.AddOverlay()
            counter += 1

            if ret == True:
                cv2.imshow('Frame', overlay_obj.image)
                cv2.waitKey(1)


    def OpenSSH(self):
        # # connect to the Jetson if we need to
        # s = pxssh.pxssh()  # see https://pexpect.readthedocs.io/en/3.x/api/pxssh.html for help - this is an extension of spawn and inherits from it
        # s.login(self.address, username="vs", password="VSrocks!", sync_multiplier=5, login_timeout=15)
        # return s

        s = paramiko.SSHClient()  #https://stackoverflow.com/questions/373639/running-interactive-commands-in-paramiko
        #https://stackoverflow.com/questions/13851846/paramiko-sftpclient-setting-missing-host-key-policy
        s.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # this allows us to nlot worry about missing key
        print(self.address)
        s.connect(self.address, username="vs", password="VSrocks!")
        return s

def ThreadingForOpenCVVideo(window, viewing_object):
    #print('Starting thread - will sleep for {} seconds'.format(seconds))
    #time.sleep(seconds)  # sleep for a while
    viewing_object.Play() #the viewing obj we created earlier
    window.write_event_value('-THREAD-', '** DONE **')  # put a message into queue for GUI

def GUI_window():
    column_right = [[sg.Text("Select your MTF Test Configuration (distances are in mm)")],
                    [sg.Checkbox('Use Config File', default=False, key="config_file_use", enable_events=True),
                     sg.Text("Choose a file: "), sg.FileBrowse(key="config_file_loc")],
                    [sg.Text('Jetson Target (name-here.local without any tcp: or port'), sg.InputText(key="targ_address")],
                    [sg.Text('serdes path starting with a slash /' ), sg.InputText(key="serdes_path")],
                    [sg.Text("Load a JSON focus calibration file"), sg.FileBrowse(key="focus_table_loc")],
                    [sg.Text('Name your test (alpha numeric + underscores only)'), sg.InputText(key="t_title")],
                    [sg.Text("Choose a folder to save in: "), sg.FolderBrowse(key="save_path")],
                    [sg.Text('Focus Distance 1'), sg.InputText(key="fd1")],
                    [sg.Text('Stage Location - Near - Focus Distance One'),  sg.InputText(key="fd1sln")],
                    [sg.Text('Stage Location - Far - Focus Distance One'),  sg.InputText(key="fd1slf")],
                    [sg.Text('Number of Pictures Per Location'), sg.InputText(key="num_picts_needed")],
                    [sg.Button("Enter Settings and Connect to Stages and Video")],
                    [sg.Button('move target up')],
                    [sg.Button('move target left'), sg.Button('move target right')],
                    [sg.Button('move target down')],
                    [sg.Text('move stage to distance (x axis'), sg.InputText(key="x_coordinate"), sg.Button('move x axis')],
                    [sg.Button("Acquire Images")]]
    layout = [[ sg.Column(column_right, element_justification='l')],]
    # cookbook https://pysimplegui.readthedocs.io/en/latest/cookbook/#getting-started-copy-these-design-patterns

    # Create the window
    window = sg.Window("MTF Test Configurator", layout)
    # Create an event loop
    while True:
        event, values = window.read()
        #print(event, values)

        if event == "config_file_use":
            if values['config_file_use'] is True:
                # if we are using the config file b/c the checkbox is checked
                # disable GUI we aren't using so we don't confuse people
                input_fields_config = ["fd1", "fd1sln", "fd1slf", "num_picts_needed", "targ_address", "serdes_path"]
                for element_key in input_fields_config:
                    #window[element_key].Update(disabled=True)  # update all those fields to disabled
                    window.Element(element_key).Update(disabled=True)
                window.Element("config_file_loc").Update(disabled=False)


            if values['config_file_use'] is False:
                input_fields_config = ["fd1", "fd1sln", "fd1slf", "num_picts_needed", "targ_address", "serdes_path"]
                for element_key in input_fields_config:
                    window.Element(element_key).Update(disabled=False)  # update all those fields to disabled
                window.Element("config_file_loc").Update(disabled=True)




        if event == "Enter Settings and Connect to Stages and Video":
            if values['config_file_use'] is True:  # if the checkbox is checked, we are using the config file
                if values['config_file_loc'] == '':  # you haven't loaded a file if it's an empty string
                    print('you need to load a config file before we can do anything')
                else:  # if you have loaded a file, the path will not me an empty string, so we can use an else
                    loc_xlsx = values['config_file_loc']
                    [where_network, where_serdes, AreaList, number_of_images] = excel_read_config(loc_xlsx)

            elif values["config_file_use"] is False:  # if the checkbox is not checked, we are entering values by hand

                number_of_images = int(values["num_picts_needed"])
                where_network = values["targ_address"]
                where_serdes = values["serdes_path"]
                # location stuff
                input_focus_one = values["fd1"]
                input_stage_one_near = values["fd1sln"]
                input_stage_one_far = values["fd1slf"]
                CloseArea = ImageArea(input_stage_one_near, input_focus_one, input_stage_one_far)
                AreaList = [CloseArea, ]  # , FarArea]

            focus_calibration_table = values['focus_table_loc']
            test_title = values["t_title"]
            save_to = values["save_path"]
            # focus_calibration = FocusStuff((values['focus_table_loc'])) # create our focus_calibration object

            viewing = View(window, where_network)
            print("before im_stage_obj")
            # viewing.Play()  # actually play
            threading.Thread(target=ThreadingForOpenCVVideo, args=(window, viewing,), daemon=True).start()
            SSH_session = viewing.OpenSSH()  # get SSH
            print("before im_stage_obj")
            im_stage_obj = ImagesAndStage(test_title, save_to, where_network, AreaList, SSH_session, number_of_images,focus_calibration_table, where_serdes)



        if event == "Acquire Images":
            im_stage_obj.capture()

        if event == 'move target up':
            # max is BOTTOM
            xyz = im_stage_obj.xyz_stage
            if xyz.z.get_current_location() <= (xyz.z.get_min()+1):
                print("can't go further, currently at " + str(xyz.z.get_current_location()) + " and min is " + str(xyz.z.get_min()))
            else:
                xyz.z.move_to(xyz.z.get_current_location() - 1)


        if event == 'move target down':
            #max is BOTTOM
            xyz = im_stage_obj.xyz_stage
            if xyz.z.get_current_location() >= (xyz.z.get_max() - 1):
                print("can't go further, currently at " + str(xyz.z.get_current_location()) + " and max is " + str(xyz.z.get_max()))
            else:
                xyz.z.move_to(xyz.z.get_current_location() + 1)

        if event == 'move target left':
            #max is right
            xyz = im_stage_obj.xyz_stage
            if xyz.y.get_current_location() <= (xyz.y.get_min() +1):
                print("can't go further, currently at " + str(xyz.y.get_current_location()) + " and min is " + str(xyz.y.get_min()))
            else:
                xyz.y.move_to(xyz.y.get_current_location() - 1)

        if event == 'move target right':
            #max is right
            xyz = im_stage_obj.xyz_stage
            if xyz.y.get_current_location() >= (xyz.y.get_max() - 1):
                print("can't go further, currently at " + str(xyz.y.get_current_location()) + " and max is " + str(xyz.y.get_max()))
            else:
                xyz.y.move_to(xyz.y.get_current_location() + 1)

        if event == 'move x axis':
            im_stage_obj.move_stage(float(values["x_coordinate"]))

        if event == sg.WIN_CLOSED:
            if 'SSH_session' in locals():
                 #SSH_session.logout() #fixme this needs to be different bc paramiko
                 pass
            window.close()
            return
# call the window!!
#f __name__ == '__main_EYEBOTH__':
GUI_window()

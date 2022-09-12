# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
#this version does not include automated camera bring up - it will work if eyeboth is functional
import os
import time
#import serdes
import vlc
#import pexpect
from pexpect import pxssh
import numpy as np
from zaber_drive import gauntry
import PySimpleGUI as sg
from datetime import datetime
from zaber_motion import Library
import pandas as pd
import json

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


def excel_read_config(loc_config):
    df = pd.read_excel(loc_config, usecols=[1])  # this is a data frame object
    # note: first ROW is Vera number and is not used! it starts counting from the first int in row 2, which is #0 in this data structure
    input_focus_one = float(df.values[0])
    input_stage_one_near = float(df.values[1])
    input_stage_one_far = float(df.values[2])
    input_focus_two = float(df.values[3])
    input_stage_two_near = float(df.values[4])
    input_stage_two_far = float(df.values[5])
    num_picts = float(df.values[6])
    CloseArea = ImageArea(input_stage_one_near, input_focus_one, input_stage_one_far)
    FarArea = ImageArea(input_stage_two_near, input_focus_two, input_stage_two_far)
    AreaList = [CloseArea, FarArea]
    print(num_picts) #fixme we don't want to print this forever - remove when things function
    return AreaList, num_picts

class FocusStuff:
    def __init__(self, filepath):
        self.table_path = filepath
        self.table_data = self.focus_json_to_coords(self.read_focus_json(filepath))


    def read_focus_json(self, filepath):
        with open(filepath, "r") as f:
            j = json.load(f)
            self.focus_table = self.focus_json_to_coords(j)
        return j

    def focus_json_to_coords(self, curve_json):
        distance = np.array(
            [int(float(dist)) for dist in sorted(curve_json["focus_lookup"].keys())],
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

    def set_focus(self, SSH_session, x_distance):
        # get values and set variables elegantly for readable/refactorable code
        focus_values = self.find_focus(self, x_distance)
        focus_value_left = focus_values[0]
        focus_value_right = focus_values[1]
        mySSH = SSH_session
        mySSH.sendline('sudo python3 serdes.py set_focus:{},{}'.format(focus_value_left, focus_value_right))
        # this is why we need SSH session
        # fixme set_focus needs implementation see autofocus.py
        pass

class ImagesAndStage:
    # feed me LIST of each location you'd like to take a picture at FOR A GIVEN FOCAL plane (near limit, focal plane, far limit)
    def __init__(self, test_title, save_to, where_network, AreaList, SSH_session, num_picts, focus_path):
        # gauntry initialization
        self.xyz_stage = gauntry()
        self.xyz_stage.home()
        # set up with y centered (for now - eventually, do something differe)
        min_y = self.xyz_stage.y.get_min()
        length_y = self.xyz_stage.y.get_max() - min_y
        dist_y = length_y/2
        self.xyz_stage.y.move_to(min_y + dist_y)
        # set up at arbitrary height (100mm)
        self.xyz_stage.z.move_to(100)
        # networking support
        self.title = test_title
        self.save_loc = str(save_to)
        self.areas = AreaList
        self.repeats = num_picts
        self.SSH_session = SSH_session
        self.tcp = "tcp://" + where_network + ":5558"
        self.focus = FocusStuff(focus_path)
        # GO take our pictures
        self.capture()

    def save_image(self, current_distance):
        # makes a file name using the test title & a timestamp
        dateTimeObj = datetime.now()
        string_distance = str(current_distance)
        file_name_current_time = 'MTF_' + str(self.title) + '_' + dateTimeObj.strftime("%d-%b-%Y-%H-%M-%S") + '_distance_' + string_distance + '.png'
        # generate an intelligible file name

        command_cap = "ffmpeg -y -i " + self.tcp + " -f image2 -frames:v 1 " + file_name_current_time
        os.system(command_cap)
        return file_name_current_time

    def move_stage(self, x_distance):
        print('moving to' + str(x_distance))
        self.xyz_stage.x.move_to(x_distance)  # move x axis to where it needs to be



    # overall motion/image capture behavior for the class
    # working_distances =[int(2), int(4)]
    def capture(self):
        for each_area in self.areas:
            # on plane
            print("about to move to focal plane:" + str(each_area.focal))
            self.move_stage(each_area.focal)
            print("setting focus")
            self.focus.set_focus(self.SSH_session,each_area.focal)
            print("saving image")

            for n in range(self.repeats):  # take this number of images
                self.save_image(each_area.focal)
                time.sleep(.3)  # wait .3 between captures)
            print("all images for this location saved")

            # near
            print("about to move to near location:" + str(each_area.near))
            self.move_stage(each_area.near)
            print("saving image")
            for n in range(self.repeats):  # take this number of images
                self.save_image(each_area.focal)
                time.sleep(.1)  # wait .3 between captures)
            print("all images for this location saved")

            # far
            print("about to move to far location:" + str(each_area.far))
            self.move_stage(each_area.far)
            print("saving image")
            for n in range(self.repeats):  # take this number of images
                self.save_image(each_area.focal)
                time.sleep(.3)  # wait .3 between captures)
            print("all images for this location saved")

# play video, open SSH if needed
class View:
    def __init__(self, test_window, network_loc):
        self.address = network_loc
        self.window = test_window

    def Play(self):
        address_stream = 'tcp://' + self.address + ':5558'  # no slashes in your input or else this will error #fixme needs error handling
        # cookbook for reference https://github.com/PySimpleGUI/PySimpleGUI/blob/master/DemoPrograms/Demo_Media_Player_VLC_Based.py
        # https://stackoverflow.com/questions/9372672/how-does-vlc-py-play-video-stream

        vlc_app = vlc.libvlc_new(1, [bytes('--no-xlib', "utf-8")])  # start VLC without a gross error! vlc_app = vlc.Instance() also works
        player = vlc_app.media_player_new()  # make a player
        our_video = vlc_app.media_new(address_stream)  # get video going
        our_video.get_mrl()
        player.set_media(our_video)  # play it
        player.set_xwindow(self.window['live_image'].Widget.winfo_id())  # send it to this specific window
        player.play()

    def OpenSSH(self):
        # connect to the Jetson if we need to
        s = pxssh.pxssh()  # see https://pexpect.readthedocs.io/en/3.x/api/pxssh.html for help - this is an extension of spawn and inherits from it
        s.login(self.address, username="vs", password="VSrocks!", sync_multiplier=5, login_timeout=15)
        return s


def GUI_window():
    column_left = [[sg.Image('', size=(1164, 872), key='live_image')]]
    column_right = [[sg.Text("Select your MTF Test Configuration")],
              [sg.Text('Jetson Target (name-here.local without any tcp: or port'), sg.InputText(key="targ_address")],
              [sg.Button("Play Video and Open SSH Connection")],
              [sg.Text("Load a JSON focus calibration file"), sg.FileBrowse(key="focus_table_loc")],
              [sg.Text('Name your test (alpha numeric + underscores only)'), sg.InputText(key="t_title")],
              [sg.Text("Choose a folder to save in: "), sg.FolderBrowse(key="save_path")],
              [sg.Checkbox('Use Config File', default=False, key="config_file_use", enable_events=True), sg.Text("Choose a file: "), sg.FileBrowse(key="config_file_loc")],
              [sg.Text('Focus Distance 1'), sg.InputText(key="fd1")],
              [sg.Text('Stage Location - Near - Focus Distance One'),  sg.InputText(key="fd1sln")],
              [sg.Text('Stage Location - Far - Focus Distance One'),  sg.InputText(key="fd1slf")],
              [sg.Text('Focus Distance 2'), sg.InputText(key="fd2")],
              [sg.Text('Stage Location - Near - Focus Distance Two'), sg.InputText(key="fd2sln")],
              [sg.Text('Stage Location - Far - Focus Distance Two'), sg.InputText(key="fd2slf")],
              [sg.Text('Number of Pictures Per Location'), sg.InputText(key="num_picts_needed")],
              [sg.Button("Enter Settings and Commence Test")]]
    layout = [[sg.Column(column_left, element_justification='c'), sg.Column(column_right, element_justification='l')]]
    # cookbook https://pysimplegui.readthedocs.io/en/latest/cookbook/#getting-started-copy-these-design-patterns

    # Create the window
    window = sg.Window("MTF Test Configurator", layout)
    # Create an event loop
    while True:
        event, values = window.read()
        #print(event, values)

        if event == "Play Video and Open SSH Connection":
            where_network = values["targ_address"]
            viewing = View(window, where_network)
            print('before play command')
            viewing.Play()  # actually play
            SSH_session = viewing.OpenSSH() #get SSH
            print('supposedly playing')

        if event == "config_file_use":
            if values['config_file_use'] is True:
                # if we are using the config file b/c the checkbox is checked
                # disable GUI we aren't using so we don't confuse people
                input_fields_config = ["fd1", "fd1sln", "fd1slf", "fd2", "fd2sln", "fd2slf", "num_picts_needed"]
                for element_key in input_fields_config:
                    #window[element_key].Update(disabled=True)  # update all those fields to disabled
                    window.Element(element_key).Update(disabled=True)
                window.Element("config_file_loc").Update(disabled=False)


            if values['config_file_use'] is False:
                input_fields_config = ["fd1", "fd1sln", "fd1slf", "fd2", "fd2sln", "fd2slf", "num_picts_needed"]
                for element_key in input_fields_config:
                    window.Element(element_key).Update(disabled=False)  # update all those fields to disabled
                window.Element("config_file_loc").Update(disabled=True)

        if event == "config_file_loc":  #and values['config_file_use'] is True:  # if we then press the browse button, we load values
            pass


        if event == "Enter Settings and Commence Test":
            focus_calibration = FocusStuff((values['focus_table_loc'])) # create our focus_calibration object
            #focus_calibration_table = focus_calibration.data
            test_title = values["t_title"]
            save_to = values["save_path"]

            if values['config_file_use'] is True:  # if the checkbox is checked, we are using the config file
                if values['config_file_loc'] == '':  # you haven't loaded a file if it's an empty string
                    print('you need to load a config file before we can do anything')
                else:   # if you have loaded a file, the path will not me an empty string, so we can use an else
                    loc_xlsx = values['config_file_loc']
                    [AreaList, number_of_images] = excel_read_config(loc_xlsx)

            elif values["config_file_use"] is False:  # if the checkbox is not checked, we are entering values by hand
                input_focus_one = values["fd1"]
                input_stage_one_near = values["fd1sln"]
                input_stage_one_far = values["fd1slf"]
                input_focus_two = values["fd2"]
                input_stage_two_near = values["fd2sln"]
                input_stage_two_far = values["fd2slf"]
                number_of_images = int(values["num_picts_needed"])
                CloseArea = ImageArea(input_stage_one_near, input_focus_one, input_stage_one_far)
                FarArea = ImageArea(input_stage_two_near, input_focus_two, input_stage_two_far)
                AreaList = [CloseArea, FarArea]

            ImagesAndStage(test_title, save_to, where_network,  AreaList, SSH_session, number_of_images, focus_calibration) #SSH_session

        if event == sg.WIN_CLOSED:
            if 'SSH_session' in locals():
                 SSH_session.logout()
            window.close()
            return

# call the window!!
#f __name__ == '__main_EYEBOTH__':
GUI_window()

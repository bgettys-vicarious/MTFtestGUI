
# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import os
import time
import sys
import subprocess
from pexpect import pxssh

import json
import cv2
import math
import glob
import numpy as np
from zaber_drive import gauntry
import PySimpleGUI as sg
from datetime import datetime



# RUN ZABER LAUNCHER FIRST OR YOU WILL GET WIERDO ERRORS

class ImageArea:
    def __init__(self, near, focal, far):
        self.near = near
        self.focal = focal
        self.far = far


class ImagesAndStage:
    # feed me LIST of each location you'd like to take a picture at FOR A GIVEN FOCAL plane (near limit, focal plane, far limit)
    def __init__(self,test_title, AreaList):
        # gauntry initialization
        #self.xyz_stage = gauntry()
        #self.xyz_stage.home()
        self.title = test_title
        self.areas = AreaList
        self.capture()


    def make_file_name(self):
        # makes a file name using the test title & a timestamp
        dateTimeObj = datetime.now()
        file_name_current_time = 'MTF_' + str(self.title) + '_' + dateTimeObj.strftime("%d-%b-%Y-%H-%M-%S") + '.png'
        return file_name_current_time

    def save_image(self, callback=None):
        # generate an intelligible file name
        filename = self.make_file_name()
        ## justin's image capture stuff from auto_image_grab.py
        try:
            os.remove("{}".format(filename))
        except:
            pass
        while True:
            try:
                os.remove(filename)
            except:
                pass
            p = subprocess.Popen(
                ['ffmpeg', '-loglevel', 'quiet', '-i', 'tcp://127.0.0.1:5558', '-f', 'image2', '-vframes', '1',
                     filename])
            try:
                p.wait(5)
            except subprocess.TimeoutExpired:
                p.kill()
                # os.system('sudo systemctl restart eye-both')
                time.sleep(5)
                if callback is not None:
                    callback()
                continue
            img = cv2.imread(filename)
            if img is None:
                # os.system('sudo systemctl restart eye-both')
                time.sleep(5)
                if callback is not None:
                    callback()
                continue
            break
        return img


    def move_stage(self, x_distance):
        print('placeholder for stage movement')
        #self.xyz_stage.x.move_to(x_distance, _async_bool=False)  #move x axis to where it needs to be

    def set_focus(self, x_distance):
        pass


    ## overall motion/image capture behavior for the class
    #working_distances =[int(2), int(4)]
    def capture(self):
        for each_area in self.areas:
            print('yay')
            #on plane
            self.move_stage(each_area.focal)
            self.set_focus(each_area.focal)
            self.save_image()
            # near
            self.move_stage(each_area.near)
            self.take_image()
            #far
            self.move_stage(each_area.far)
            self.take_image()

class ImageStream:
    def __init__(self, where_network):
        self.address = where_network
        self.Stream()

    def Stream (self):
        ## ssh-askpass needs to be installed for this to work

        s = pxssh.pxssh()  #see https://pexpect.readthedocs.io/en/3.x/api/pxssh.html for help - this is an extension of spawn and inherits from it
        # print(where_network)
        s.login(self.address, username="vs", password="VSrocks!")

        command_nvp = 'sudo nvpmodel -m 0'
        command_clock = 'sudo /usr/bin/jetson_clocks'
        command_restart_nvargus = 'sudo systemctl restart nvargus-daemon'
        command_stop_eyeboth = 'sudo systemctl stop eye-both'
        command_serdes_1 = 'sudo python3 serdes.py ub954_reset_pin'
        command_serdes_2 = 'sudo python3 serdes.py setup_fpd:False'
        command_serdes_3 = 'sudo python3 serdes.py led_set:0'
        command_v4l2 = 'v4l2-ctl --set-fmt-video=width=2328,height=1744,pixelformat=RG10 --set-ctrl bypass_mode=0 --stream-mmap --stream-count=0 --stream-to=/dev/null'

        command_list = [command_nvp, command_clock, command_restart_nvargus, command_stop_eyeboth, command_serdes_1, command_serdes_2, command_serdes_3, command_v4l2]

        for command in command_list:
            s.sendline(command)  # run a command
            s.prompt()  # match the prompt
            print("input was:"+ str(s.before.decode("utf-8"))) #print it without b' which means bytes https://stackoverflow.com/questions/35585158/python-pexpect-regex-match-is-encased-in-b


        #### INDIVIDUAL COMMAND SENDING
        # s.sendline(command_nvp)  # run a command
        # s.prompt()  # match the prompt
        # print("input was:"+ str(s.before.decode("utf-8"))) #print it without b' which means bytes https://stackoverflow.com/questions/35585158/python-pexpect-regex-match-is-encased-in-b

        # s.sendline(command_clock)
        # s.prompt()
        # print("input was:" + str(s.before.decode("utf-8")))
        # s.sendline(command_restart_nvargus)
        # s.prompt()
        # print("input was:" + str(s.before.decode("utf-8")))



        # subprocess.run(command_nvp.split())
        # subprocess.run(command_clock.split())
        # subprocess.run(command_restart_nvargus.split())
        # subprocess.run(command_stop_eyeboth.split())
        # subprocess.run(command_serdes_1.split())
        # subprocess.run(command_serdes_2.split())
        # subprocess.run(command_serdes_3.split())
        # subprocess.run(command_v4l2.split())










def GUI_window():
    layout = [[sg.Text("Select your MTF Test Configuration")],
              [sg.Text('Jetson Target'), sg.InputText(key="targ_address")],
              [sg.Button("Connect to Jetson")],
              [sg.Text('Name your test (alpha numeric + underscores only)'), sg.InputText(key="t_title")],
              [sg.Text('Focus Distance 1'), sg.InputText(key="fd1")],
              [sg.Text('Stage Location - Near - Focus Distance One'),  sg.InputText(key="fd1sln")],
              [sg.Text('Stage Location - Far - Focus Distance One'),  sg.InputText(key="fd1slf")],
              [sg.Text('Focus Distance 2'), sg.InputText(key="fd2")],
              [sg.Text('Stage Location - Near - Focus Distance Two'), sg.InputText(key="fd2sln")],
              [sg.Text('Stage Location - Far - Focus Distance Two'), sg.InputText(key="fd2slf")],
              [sg.Button("Enter Settings and Commence Test")]]
    #cookbook https://pysimplegui.readthedocs.io/en/latest/cookbook/#getting-started-copy-these-design-patterns


    # Create the window
    window = sg.Window("MTF Test Configurator", layout)

    # Create an event loop
    while True:
        event, values = window.read()
        # End program if user closes window or
        # presses the OK button
        if event == "Connect to Jetson":
            # need to do an SSH connection here
            where_network = values["targ_address"]
            stream = ImageStream(where_network)
        if event == "Enter Settings and Commence Test" or event == sg.WIN_CLOSED:
            break

    window.close()

    where_network = values["targ_address"]
    test_title = values ["t_title"]
    input_focus_one = values["fd1"]
    input_stage_one_near = values["fd1sln"]
    input_stage_one_far = values["fd1slf"]
    input_focus_two = values["fd2"]
    input_stage_two_near = values["fd2sln"]
    input_stage_two_far = values["fd2slf"]

    CloseArea = ImageArea(input_stage_one_near, input_focus_one, input_stage_one_far)
    FarArea = ImageArea(input_stage_two_near, input_focus_two, input_stage_two_far)
    return test_title, where_network, CloseArea, FarArea, stream


### call the window!!
if __name__ == '__main__':
    [test_title, where_network, CloseArea, FarArea] = GUI_window()
    #where_network = "damp-affair.local"
    stream = ImageStream(where_network)
    #backend = ImagesAndStage(test_title, [CloseArea, FarArea])


# See PyCharm help at https://www.jetbrains.com/help/pycharm/

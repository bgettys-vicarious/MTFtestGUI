
# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import os
import time
import vlc
import sys
import subprocess
import pexpect
from pexpect import pxssh
import cv2
import math
import glob
import numpy as np
from zaber_drive import gauntry
import PySimpleGUI as sg
from datetime import datetime

from zaber_motion import Library

#make sure zaber has a database
Library.enable_device_db_store() #fixme, eventually I need to change this to the second offline method explained HERE: https://www.zaber.com/software/docs/motion-library/ascii/howtos/device_db/



# RUN ZABER LAUNCHER FIRST OR YOU WILL GET WIERDO ERRORS

class ImageArea:
    def __init__(self, near, focal, far):
        self.near = float(near)
        self.focal = float(focal)
        self.far = float(far)

class ImagesAndStage:
    # feed me LIST of each location you'd like to take a picture at FOR A GIVEN FOCAL plane (near limit, focal plane, far limit)
    def __init__(self,test_title, save_to, where_network, SSH_session, AreaList):
        # gauntry initialization
        self.xyz_stage = gauntry()
        self.xyz_stage.home()
        #networking support
        self.title = test_title
        self.save_loc = str(save_to)
        self.areas = AreaList
        self.SSH_session = SSH_session
        self.tcp = "tcp://" + where_network + ":5558"
        #GO
        self.capture()


    def save_image(self, current_distance):
        # makes a file name using the test title & a timestamp
        dateTimeObj = datetime.now()
        string_distance = str(current_distance)
        file_name_current_time =  'MTF_' + str(self.title) + '_' + dateTimeObj.strftime("%d-%b-%Y-%H-%M-%S") + '_distance_' + string_distance + '.png'
        # generate an intelligible file name
        cd_command = 'cd ' + self.save_loc
        os.system(cd_command)
        command_cap = "ffmpeg -y -i " + self.tcp + " -f image2 -frames:v 1 " + file_name_current_time
        os.system(command_cap)
        return file_name_current_time

    def move_stage(self, x_distance):
        print('moving to' + str(x_distance))
        self.xyz_stage.x.move_to(x_distance)  #move x axis to where it needs to be

    def set_focus(self, x_distance):
        #this is why we need SSH session
        pass

    ## overall motion/image capture behavior for the class
    #working_distances =[int(2), int(4)]
    def capture(self):
        for each_area in self.areas:
            #on plane
            print("about to move to focal plane:" + str(each_area.focal))
            self.move_stage(each_area.focal)
            print ("setting focus")
            self.set_focus(each_area.focal)
            print ("saving image")
            self.save_image(each_area.focal)

            # near
            print("about to move to near location:" + str(each_area.near))
            self.move_stage(each_area.near)
            print ("saving image")
            self.save_image(each_area.near)
            print("image saved")

            #far
            print("about to move to far location:" + str(each_area.far))
            self.move_stage(each_area.far)
            print ("saving image")
            self.save_image(each_area.far)
            print("image saved")

class ImageStream:
    def __init__(self, where_network):
        self.address = where_network
        [s, view_state] = self.Stream()
        self.SSH = s
        self.view_state = view_state

    def gstreamer_start(self, s):
        gstreamer_command = """gst-launch-1.0 -v nvarguscamerasrc sensor-id=0 sensor-mode=0 maxperf=true awblock=false aelock=true \
                    exposurecompensation=0 ispdigitalgainrange="1 1" ! "video/x-raw(memory:NVMM), width=(int)2328, \
                    height=(int)1744, framerate=(fraction)150/1" ! nvvidconv ! "video/x-raw(memory:NVMM), width=(int)2048, height=(int)1524" \
                    ! omxh264enc qos=true vbv-size=2 MeasureEncoderLatency=true profile=8 bitrate=30000000 control-rate=2 insert-sps-pps=true \
                    SliceIntraRefreshEnable=true SliceIntraRefreshInterval=270 ! 'video/x-h264' ! matroskamux ! tcpserversink host=0.0.0.0 port=5558 async=false"""
        s.sendline(gstreamer_command)
        print("input was:" + str(s.before.decode("utf-8")))
        outcome2 = s.expect(
            ['x-matroska', 'Could not open', pexpect.EOF, pexpect.TIMEOUT], timeout=10)

        view_state = 1  # if this is 0, you can view - only change this if thigns are HEALTHY

        if outcome2 == 0:
            # success
            print("pipe successfully initialized in gstreamer")
            view_state = 0

        elif outcome2 == 1:
            print("pipeline already running, attempting to kill and restart....")
            # pipeline already running
            s.sendcontrol('c')  # code for control c - get rid of all those prints so things work better
            os.system('scp reset.sh vs@many-phone.local:/home/vs/') #from THIS computer
            try:
                #os.system('ssh vs@many-phone.local bash reset.sh')
                s.sendline('bash reset.sh')
                s.prompt()
                print(s.before.decode("utf-8"))
            except:
                raise Exception(" find becca")

            # try to restart gstreamer
            s.sendline(gstreamer_command)

            # now see if the restart attempt works
            outcome3 = s.expect(['x-matroska', pexpect.EOF, pexpect.TIMEOUT], timeout=10)
            if outcome3 == 0:
                print("pipe successfully initialized in gstreamer")
                view_state = 0
            elif outcome3 == 1:
                print("the program quit/stream not initialized. Something's wrong")
                quit()
            elif outcome3 == 2:
                print("we timed out. Is the network up? try pinging your Jetson.")
                quit()
            else:
                print("Something's borked. Find Becca.")
                quit()

        elif outcome2 == 2:
            # eof
            print("the program quit/stream not initialized. Something's wrong")
            quit()
        elif outcome2 == 3:
            # timeout
            print(
                "we timed out. Either the program didn't get an expected response, or  the network is down. try pinging your Jetson.")
            quit()
        else:
            # some other exception
            print("Something's borked. Find Becca.")
            quit()
        return view_state

    def stream_prep(self):
        ## ssh-askpass needs to be installed for this to work

        s = pxssh.pxssh()  #see https://pexpect.readthedocs.io/en/3.x/api/pxssh.html for help - this is an extension of spawn and inherits from it
        s.login(self.address, username="vs", password="VSrocks!", sync_multiplier=5 )

        command_nvp = 'sudo nvpmodel -m 0'
        command_clock = 'sudo /usr/bin/jetson_clocks'
        command_restart_nvargus = 'sudo systemctl restart nvargus-daemon'
        command_stop_eyeboth = 'sudo systemctl stop eye-both'
        command_serdes_1 = 'sudo python3 serdes.py ub954_reset_pin'
        command_serdes_2 = 'sudo python3 serdes.py setup_fpd:False'
        command_serdes_3 = 'sudo python3 serdes.py led_set:0'
        command_v4l2 = 'v4l2-ctl --set-fmt-video=width=2328,height=1744,pixelformat=RG10 --set-ctrl bypass_mode=0 --stream-mmap --stream-count=100 --stream-to=/dev/null'

        command_list = [command_nvp, command_clock, command_restart_nvargus, command_stop_eyeboth, command_serdes_1, command_serdes_2, command_serdes_3]

        for command in command_list:
            s.sendline(command)  # run a command
            s.prompt()  # match the prompt
            test = str(s.before.decode("utf-8")) #print it without b' which means bytes https://stackoverflow.com/questions/35585158/python-pexpect-regex-match-is-encased-in-b
            print("input was:"+ test)


        #pexpect has built in exception handling, how pleasant!
        s.sendline(command_v4l2)
        outcome = s.expect(['fps', pexpect.EOF, pexpect.TIMEOUT], timeout=10)
        #print(outcome)
        #s.prompt()


        if outcome == 0:
            #s.sendcontrol('c') #code for control c
            #s.prompt()
            print("stream detected. please hold....")
        elif outcome == 1:
            raise Exception("the program quit/stream not initialized. Something's wrong")
        elif outcome == 2:
            raise Exception("we timed out. Is the network up? try pinging your Jetson.")
        else:
            print("Something's borked. Find Becca.")
        return s


    def Stream(self):
        s = self.stream_prep()
        view_state = self.gstreamer_start(s) #THIS IS THE METHOD FOR GETTING GSTREAMER GOING. IT RETUNRS VIEW_STATE IF YOU FEED IT YOUR S (PEXPECT SESSION)
        return s, view_state


class View:
    def __init__(self, test_window, network_loc):
        self.address = network_loc
        self.window = test_window
        #self.Play()  # get VLC playing out stream

    def Play(self):
        address_stream = 'tcp://' + self.address + ':5558'  ##no slashes in your input or else this will error #fixme needs error handling
        # cookbook for reference https://github.com/PySimpleGUI/PySimpleGUI/blob/master/DemoPrograms/Demo_Media_Player_VLC_Based.py
        #https://stackoverflow.com/questions/9372672/how-does-vlc-py-play-video-stream

        vlc_app = vlc.libvlc_new(1,[bytes('--no-xlib', "utf-8")]) #start VLC without a gross error!
        #vlc_app = vlc.Instance()  # start vlc instance
        player = vlc_app.media_player_new() #make a player
        our_video = vlc_app.media_new(address_stream) #get video going
        our_video.get_mrl()
        player.set_media(our_video)  #play it
        player.set_xwindow(self.window['live_image'].Widget.winfo_id()) #send it to this specific window
        player.play()

    def OpenSSH(self):
        #connect to the Jetson if we need to
        s = pxssh.pxssh()  # see https://pexpect.readthedocs.io/en/3.x/api/pxssh.html for help - this is an extension of spawn and inherits from it
        # print(where_network)
        s.login(self.address, username="vs", password="VSrocks!", sync_multiplier=5, login_timeout=15)
        return s



def GUI_window():
    column_left = [[sg.Image('', size=(1164, 872), key='live_image')]]
    column_right= [[sg.Text("Select your MTF Test Configuration")],
              [sg.Text('Jetson Target'), sg.InputText(key="targ_address")],
              [sg.Button("Start Jetson Stream"), sg.Checkbox('Jetson is Already Streaming', default=False, key="JetsonAlreadyRunning"), sg.Button("Play Video")],
              [sg.Text('Name your test (alpha numeric + underscores only)'), sg.InputText(key="t_title")],
              [sg.Text('Path to Save To'), sg.InputText(key="save_path")],
              [sg.Text('Focus Distance 1'), sg.InputText(key="fd1")],
              [sg.Text('Stage Location - Near - Focus Distance One'),  sg.InputText(key="fd1sln")],
              [sg.Text('Stage Location - Far - Focus Distance One'),  sg.InputText(key="fd1slf")],
              [sg.Text('Focus Distance 2'), sg.InputText(key="fd2")],
              [sg.Text('Stage Location - Near - Focus Distance Two'), sg.InputText(key="fd2sln")],
              [sg.Text('Stage Location - Far - Focus Distance Two'), sg.InputText(key="fd2slf")],
              [sg.Button("Enter Settings and Commence Test")]]
    layout = [[sg.Column(column_left, element_justification='c'), sg.Column(column_right, element_justification='l')]]
    # cookbook https://pysimplegui.readthedocs.io/en/latest/cookbook/#getting-started-copy-these-design-patterns


    # Create the window
    window = sg.Window("MTF Test Configurator", layout)
    # Create an event loop
    while True:
        event, values = window.read()
        # End program if user closes window or
        # presses the OK button

        if event == "Start Jetson Stream":
            # need to do an SSH connection here
            where_network = values["targ_address"]
            our_comp = ImageStream(where_network)  #starts the pipeline and tells us if it is viewable/healthy or not and creates the SSH objects we need later
            SSH_session = our_comp.SSH
            view_state = our_comp.view_state
            SSH_state = 1

        if event == "Play Video":
            if 'view_state' in locals(): # if this has even been created
                if view_state == 0:
                    # where_network = values["targ_address"] #don't need this, it's defined above in this case
                    #instantiate a view object
                    viewing = View(window, where_network)
                    viewing.Play()
                else:
                    print("your stream has issues, try again.")
            else:
                if values['JetsonAlreadyRunning'] == True:
                    where_network = values["targ_address"]
                    viewing = View(window, where_network)
                    print('starting SSH')
                    SSH_session = viewing.OpenSSH()  # make sure we have an SSH session to command the camera with
                    print('before play command')
                    viewing.Play() #actually play
                    print('supposedly playing')
                else:
                    print("you haven't RUN the stream yet, goofball")

        if event == "Enter Settings and Commence Test":
            test_title = values["t_title"]
            save_to = values ["save_path"]
            input_focus_one = values["fd1"]
            input_stage_one_near = values["fd1sln"]
            input_stage_one_far = values["fd1slf"]
            input_focus_two = values["fd2"]
            input_stage_two_near = values["fd2sln"]
            input_stage_two_far = values["fd2slf"]


            CloseArea = ImageArea(input_stage_one_near, input_focus_one, input_stage_one_far)
            FarArea = ImageArea(input_stage_two_near, input_focus_two, input_stage_two_far)
            AreaList = [CloseArea,FarArea]
            ImagesAndStage(test_title, save_to, where_network, SSH_session, AreaList)

        if event == sg.WIN_CLOSED:
            SSH_session.logout()
            window.close()



### call the window!!
if __name__ == '__main__':
    #[test_title, where_network, CloseArea, FarArea] = GUI_window()
    GUI_window()
    #quit() ## don't leave a giant mess, Becca!


from PIL import Image, ImageTk
from urllib import request
import PySimpleGUI as sg
import cv2
import vlc
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

class View:
    def __init__(self, test_window):
        self.window = test_window

    def Play(self):
        address_stream = 'tcp://' + 'unknown-tax.local'+ ':5558'  # no slashes in your input or else this will error #fixme needs error handling
        # # cookbook for reference https://github.com/PySimpleGUI/PySimpleGUI/blob/master/DemoPrograms/Demo_Media_Player_VLC_Based.py
        # # https://stackoverflow.com/questions/9372672/how-does-vlc-py-play-video-stream
        #
        # vlc_app = vlc.libvlc_new(1, [bytes('--no-xlib', "utf-8")])  # start VLC without a gross error! vlc_app = vlc.Instance() also works
        # player = vlc_app.media_player_new()  # make a player
        # our_video = vlc_app.media_new(address_stream)  # get video going
        # our_video.get_mrl()
        # player.set_media(our_video)  # play it
        # player.set_xwindow(self.window['live_image'].Widget.winfo_id())  # send it to this specific window
        # our_image = self.window['live_image'].Widget.image
        # player.play()
        # return our_image


# filename = 'test_img.png'
# size = (1164, 872)
# im = Image.open(filename)
# im = im.resize(size, resample=Image.BICUBIC)
#
#
#


address_stream = 'tcp://' + 'unknown-tax.local'+ ':5558'
vid = cv2.VideoCapture(address_stream)
counter = 0
while(vid.isOpened()):
    ret, frame = vid.read()
    frame = cv2.resize(frame, (1164, 872)) #downscale ahead of time
    if counter == 0:
        overlay_obj = PositionOverlay(frame, counter)
    else:
        overlay_obj.image = frame
    overlay_obj.AddOverlay()
    counter += 1
    if ret == True:
        cv2.imshow('Frame', overlay_obj.image)
        cv2.waitKey(1)

# testing the PositionOverlay class
# img = cv2.imread('test_img.png')
# counter = 0
# PositionOverlay(img, counter)
# cv2.imshow('img', img)
# cv2.waitKey()

# #column_left= [[sg.Image('', size=(1164, 872), key='live_image')]]
# column_left = [[sg.Graph((600,450),(0,450), (600,0), key='live_image', enable_events=True, drag_submits=True)],]
# column_right = [[sg.Button("Play Video and Open SSH Connection", key="playandssh")],]
# layout = [[sg.Column(column_left, element_justification='c'), sg.Column(column_right, element_justification='l')]]
#
# window = sg.Window('Window Title', layout)
# graph_element = window['live_image']
#
#
#
# while True:
#     event, values = window.read()
#
#     if event == "playandssh":
#         print('play video pressed')
#         # viewing = View(window)
#         # img = viewing.Play()  # actually play
#         # cv2.imread(img)
#         # cv2.imshow('img', img)
#     if event == sg.WIN_CLOSED:
#         break
#
#
# window.close()



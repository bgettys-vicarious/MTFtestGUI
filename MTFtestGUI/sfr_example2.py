from __future__ import print_function
import os
import sys
import subprocess
import json
import cv2
import math
import glob
import numpy as np
import time
import matplotlib.pyplot as plt
from imatest.it import ImatestLibrary, ImatestException

# Sample code that calls the Imatest IT Python library.
#
# This code will  execute the Imatest SFR function on the
# file 'sfr_example.jpg' which should be a capture of an SFRplus test chart.
#
# The SFR module measures MTF and related results from slanted edges.
#
# For more information, visit http://www.imatest.com/docs/sfr_instructions/
#
# In this example program, the 'sfr_example.jpg' files should be located
# in the same directory as this example script, and the 'imatest-v2.ini' file
# should be located in the "ini_file" directory in the Python samples directory.
#
# Certain diagnostic lines are written to standard out for diag.
current_ini_file = './imatest-v2.ini'
high_level_folder = 'regular_no_noise_option1'
    # and write everything back
def imatest_analyze(imatest, input_file):
    print(input_file)
    root_dir = os.path.dirname(os.path.realpath(__file__))
    op_mode = ImatestLibrary.OP_MODE_SEPARATE
    ini_file = current_ini_file
    mtf = [-1, -1]
    lwph = -1
    try:
        result = imatest.sfr(input_file=input_file,
                             root_dir=root_dir,
                             op_mode=op_mode,
                             ini_file=ini_file)

        # print(result)
        result = json.loads(result)
        mtf = np.array(result['sfrResults']['mtf50']).reshape(-1, 2)
        mtf = np.max(mtf, axis=1)
        print(mtf)
        lwph = np.max(np.array(result['sfrResults']['mtf50p_LWPH_summary']))
    except ImatestException as iex:
        if iex.error_id == ImatestException.FloatingLicenseException:
            print("All floating license seats are in use.  Exit Imatest on another computer and try again.")
        elif iex.error_id == ImatestException.LicenseException:
            print("License Exception: " + iex.message)
        else:
            print(iex.message)

        exit_code = iex.error_id
    except Exception as ex:
        print(str(ex))
        exit_code = 1
    return mtf, lwph

def update_imi_file(data, vert, hor, shape):
    # roi_mult = [ 1716 1174 1878 1425; 45 1196 207 1444; 3681 1161 3843 1407; 1711 179 1873 429; 1722 2175 1884 2425;]
    # ex [ 2309  392 3408  765; 2209 1955 3345 2341; 3300  801 3732 2069; 1908  670 2330 1913;]
    line = 553
    vert = [[i[0][0], i[2][0]] for i in vert]
    hor = [[i[0][0], i[2][0]] for i in hor]
    coords = np.array([vert, hor]).flatten().reshape(-1,4)
    # print(coords)
    # import pdb; pdb.set_trace()
    print(data[line])
    arrays = [" ".join(str(i)[1:-1].split()) for i in coords]
    # import pdb; pdb.set_trace()
    string = 'roi_mult = [ {};]\n'.format("; ".join(arrays))
    print(string)
    data[line] = string
    line += 1
    string = 'nwid_save = {}\n'.format(shape[1])
    data[line] = string
    line += 1
    string = 'nht_save = {}\n'.format(shape[0]) # height
    data[line] = string
    line += 1
    with open(current_ini_file, 'w') as file:
        file.writelines( data )

def analyze_images(imatest, ini_data, folder_name):
    images = sorted(glob.glob('{}/*.png'.format(folder_name)))
    # images = [images[-7]]
    nominal_distance = int(folder_name.split('distance_')[-1].split('mm')[0])
    mtfs = {}
    for image_path in images:
        try:
            print('working on: {}'.format(image_path))
            distance_check = int(image_path.split('distance_')[-1][:-4])
            if distance_check > 110 and nominal_distance < 45: continue
            print(distance_check)
            # distance_check = int(distance_check.split('.png')[0])
            #image_path = '/Users/justinkeenan/Downloads/test_4096x3496_no_noise_90.png'
            image = cv2.imread(image_path, cv2.IMREAD_COLOR)
            image_center = np.array(image.shape[:2])/2
            original = image.copy()
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            blur = cv2.GaussianBlur(gray,(5,5),0)
            if distance_check > 90:
                area = 501
            else:
                area = 1001
            print(area)
            thresh = cv2.adaptiveThreshold(blur, 255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY,area,-3)
            thresh2 = cv2.threshold(blur, 100, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
            if image_center[1] < 2000 or distance_check < 40:
                kernel = np.ones((5,5), np.uint8)
            else:
                kernel = np.ones((11,11), np.uint8)

            thresh = cv2.dilate(thresh, kernel, iterations=1)
            thresh = cv2.erode(thresh, kernel, iterations=3)
            # thresh = cv2.dilate(thresh, kernel, iterations=3)
            if distance_check < 60:
                thresh = cv2.erode(thresh, kernel, iterations=4)
            if distance_check < 40:
                thresh = cv2.erode(thresh, kernel, iterations=20)
            if distance_check < 60:
                thresh = cv2.dilate(thresh, kernel, iterations=4)
            if distance_check < 40:
                thresh = cv2.dilate(thresh, kernel, iterations=30)
                thresh = cv2.erode(thresh, kernel, iterations=10)
            cv2.imwrite('{}_thresh.png'.format(image_path.split('/')[-1][:-4]), thresh)
            # cv2.imwrite('{}_thresh2.png'.format(image_path.split('/')[-1][:-4]), thresh2)
            
            edges = cv2.Canny(thresh,50,150,apertureSize = 7)
            cv2.imwrite('{}_edges.png'.format(image_path.split('/')[-1][:-4]), edges)
            
            # cv2.imwrite("edges.png", edges)
            # cv2.imwrite('{}_edges.png'.format(image_path.split('/')[-1][:-4]), edges)

            # minLineLength=100
            # lines = cv2.HoughLinesP(image=edges,rho=1,theta=np.pi/180, threshold=100,lines=np.array([]), minLineLength=minLineLength,maxLineGap=80)
            # a,b,c = lines.shape
            # for i in range(a):
            #     cv2.line(image, (lines[i][0][0], lines[i][0][1]), (lines[i][0][2], lines[i][0][3]), (0, 255, 255), 3, cv2.LINE_AA)

            # cv2.imwrite('houghlines5.png',image)

            cnts = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            remove = []
            for index, i in enumerate(cnts[1][0]):
                # print(i)
                if i[2] != -1:
                    remove.append(index)
            # remove = []

            new_cnts = np.delete(cnts[1][0], remove)
            cnts = np.delete(cnts[0], remove)

            #cnts = cnts[0] if len(cnts) == 2 else cnts[1]
            cnts = sorted(cnts, key = cv2.contourArea, reverse = True)[:]
            ROI_number = 0
            
            contours = []
            for c in cnts:
                peri = cv2.arcLength(c, True)
                approx = cv2.approxPolyDP(c, 0.015 * peri, True)

                cv2.drawContours(original, [c], 0, (255,0,0), 3)

                # if len(approx) < 7:
                #     cv2.drawContours(original, [approx], 0, (255,255,0), 3)
                # print(approx)
                if distance_check < 50:
                    contours.append([c, approx])
                if len(approx) == 4:
                    contours.append([c, approx])

            true_contour = contours[0]
            distance_to_center = 99999999999
            if distance_check > 50:
                for c in contours:
                    center = np.average(c[1], axis=0)[0]
                    cv2.drawContours(original, [c[1]], 0, (0,255,0), 3)
                    # print(center, image_center)
                    dx = abs(center[0]-image_center[1])
                    dy = abs(center[1]-image_center[0])
                    R = np.max(image_center)/3
                    k = R/np.sqrt(2)
                    # print(k, dx, dy)
                    # if dx <= k and dy <= k: 
                    #     true_contour = c
                    #     break

                    distance = dx**2 + dy**2
                    area = cv2.contourArea(c[0])
                    print(distance, center, dx, dy, area)
                    if area < 2000: continue
                    if distance < distance_to_center:
                        print('new center')
                        distance_to_center = distance
                        true_contour = c

            cv2.drawContours(original, [true_contour[1]], 0, (0,0,255), 3)
            # cv2.imwrite('{}_ROI_{}.png'.format(image_path.split('/')[-1][:-4], ROI_number), original)
            ROI_number += 1

            four_boxes = []
            corners = [i[0] for i in true_contour[1]]
            edges = [[corners[i], corners[i+1]] for i in range(3)]
            edges.append([corners[3], corners[0]])
            vertical = []
            horizontal = []
            scale = 0.8
            horizontal_scale = 0.34
            for i in edges:
                center = np.average(i, axis=0)
                if abs(i[0][0] - i[1][0]) > abs(i[0][1] - i[1][1]):
                    # horizontal
                    length = abs(i[0][0] - i[1][0]) * scale
                    width = length * horizontal_scale
                    box = [
                        [[center[0] - length/2, center[1] - width/2]],
                        [[center[0] - length/2, center[1] + width/2]],
                        [[center[0] + length/2, center[1] + width/2]],
                        [[center[0] + length/2, center[1] - width/2]]
                    ]
                    # print(box)
                    vertical.append(np.array(box).astype(np.int32))
                else:
                    # vertical
                    length = abs(i[0][1] - i[1][1]) * scale
                    width = length * horizontal_scale
                    box = [
                        [[center[0] - width/2, center[1] - length/2]],
                        [[center[0] - width/2, center[1] + length/2]],
                        [[center[0] + width/2, center[1] + length/2]],
                        [[center[0] + width/2, center[1] - length/2]]
                    ]
                    # print(box)
                    horizontal.append(np.array(box).astype(np.int32))

            for i in vertical:
                cv2.drawContours(original, [i], 0, (0,255,0), 3)
            for i in horizontal:
                cv2.drawContours(original, [i], 0, (255,0,0), 3)
            cv2.imwrite('{}_Box_{}.png'.format(image_path.split('/')[-1][:-4], ROI_number), original)
            ROI_number += 1
            # print(vertical, horizontal)
            update_imi_file(ini_data, vertical, horizontal, np.array(image.shape))
            mtf, lwph = imatest_analyze(imatest, image_path)
            if math.isnan(mtf[0]):
                mtf[0] = -1
            if math.isnan(mtf[1]):
                mtf[1] = -1
            if math.isnan(lwph):
                lwph = -1
            distance = int(image_path.split('/')[-1][:-4].split('_')[-1])
            mtfs[distance] = {'h': mtf[0], 'v': mtf[1], "lw": lwph}
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(e)

    print(mtfs)
    print(folder_name)
    with open(folder_name+'.json', 'w') as f:
        # np.save(f, np.array(mtfs))
        json.dump(mtfs, f, allow_nan=True)

    fig, ax = plt.subplots()
    data = []
    for dist in mtfs.keys():
        data.append([dist, mtfs[dist]['lw']])

    data = np.array(data)
    data = data[np.argsort(data[:,0])]
    plt.plot(data[:,0], data[:,1])
    ax.set_xlabel('Distance to target (mm)')
    ax.set_ylabel('Mtf50p (LW/PH)')
    ax.set_title('{}mm Focus: {}'.format(nominal_distance, high_level_folder))
    fig.savefig('{}.png'.format(folder_name))
    # plt.show()
    # time.sleep(1)
    # plt.close()
#
# This uses a compiled Python shared library built by the MATLAB Compiler.
def analyze():
    exit_code = 0
    root_dir = os.path.dirname(os.path.realpath(__file__))
    images_dir = os.path.join(root_dir, os.pardir, os.pardir, 'images')

    # Initialize Imatest Library
    imatest = ImatestLibrary()

    ini_file = os.path.join(root_dir, os.pardir, 'ini_file', r'imatest-v2.ini')

    with open(ini_file, 'r') as file:
        # read a list of lines into data
        data = file.readlines()

    folders = sorted(glob.glob('/home/research/mtf_data/{}/*'.format(high_level_folder)))
    folders = [path for path in folders if os.path.isdir(path)]
    print(folders)
    # exit(0)
    folders = [folders[17]]
    print(folders)
    # exit(0)
    for folder in folders:
        analyze_images(imatest, data, folder)

    # When finished terminate the library
    imatest.terminate_library()

    exit(exit_code)

if __name__ == "__main__":
    if sys.platform == 'darwin':
        # On macOS, Python code that calls IT must be called through the mwpython script provided by Mathworks. While
        # this is not an issue when calling python from the command line to run a script, many Python IDE's will not
        # allow the forwarding of the call to mwpython. Below is a recursive example how to forward the call in a manner
        # that Python IDE's can run and still debug.
        if 'MWPYTHON_FORWARD' not in os.environ:
            file_path = os.path.abspath(__file__)

            command = ['/Applications/MATLAB/MATLAB_Runtime/v99/bin/mwpython', file_path]

            # Set an environment variable to halt recursion
            os.environ['MWPYTHON_FORWARD'] = '1'

            # Set the PYTHONHOME environment variable so that the mwpython script can correctly detect the
            # Python version
            os.environ['PYTHONHOME'] = sys.exec_prefix

            completed_process = subprocess.run(command, env=os.environ)

            exit(completed_process.returncode)
        else:
            analyze()
    else:
        analyze()
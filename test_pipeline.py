#!/usr/bin/env python
import os
import json
import torch
import pprint
import argparse

import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")
import cv2
from tqdm import tqdm
from config import system_configs
from nnet.py_factory import NetworkFactory
from db.datasets import datasets
import importlib
from RuleGroup.Cls import GroupCls
from RuleGroup.Bar import GroupBar
from RuleGroup.LineQuiry import GroupQuiry
from RuleGroup.LIneMatch import GroupLine
from RuleGroup.Pie import GroupPie
import math
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
torch.backends.cudnn.benchmark = False
import requests
import time
import re
import pytesseract


def parse_args():
    parser = argparse.ArgumentParser(description="Test CornerNet")
    parser.add_argument("--cfg_file", dest="cfg_file", help="config file", default="CornerNetLine", type=str)
    parser.add_argument("--testiter", dest="testiter",
                        help="test at iteration i",
                        default=50000, type=int)
    parser.add_argument("--split", dest="split",
                        help="which split to use",
                        default="validation", type=str)
    parser.add_argument('--cache_path', dest="cache_path", type=str)
    parser.add_argument('--result_path', dest="result_path", type=str)
    parser.add_argument('--tar_data_path', dest="tar_data_path", type=str)
    parser.add_argument("--suffix", dest="suffix", default=None, type=str)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--data_dir", dest="data_dir", default="data/linedata(1028)", type=str)
    parser.add_argument("--image_dir", dest="image_dir",
                        default="C:/work/linedata(1028)/line/images/test2019/f4b5dac780890c2ca9f43c3fe4cc991a_d3d3LmVwc2lsb24uaW5zZWUuZnIJMTk1LjEwMS4yNTEuMTM2.xls-3-0.png",
                        type=str)
    args = parser.parse_args()
    return args

def make_dirs(directories):
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
def load_net(testiter, cfg_name, data_dir, cache_dir, result_dir, cuda_id=0):
    cfg_file = os.path.join(system_configs.config_dir, cfg_name + ".json")
    with open(cfg_file, "r") as f:
        configs = json.load(f)
    configs["system"]["snapshot_name"] = cfg_name
    configs["system"]["data_dir"] = data_dir
    configs["system"]["cache_dir"] = cache_dir
    configs["system"]["result_dir"] = result_dir
    configs["system"]["tar_data_dir"] = "Cls"
    system_configs.update_config(configs["system"])

    train_split = system_configs.train_split
    val_split = system_configs.val_split
    test_split = system_configs.test_split

    split = {
        "training": train_split,
        "validation": val_split,
        "testing": test_split
    }["validation"]

    result_dir = system_configs.result_dir
    result_dir = os.path.join(result_dir, str(testiter), split)

    make_dirs([result_dir])

    test_iter = system_configs.max_iter if testiter is None else testiter
    print("loading parameters at iteration: {}".format(test_iter))
    dataset = system_configs.dataset
    db = datasets[dataset](configs["db"], split)
    print("building neural network...")
    nnet = NetworkFactory(db)
    print("loading parameters...")
    nnet.load_params(test_iter)
    if torch.cuda.is_available():
        nnet.cuda(cuda_id)
    nnet.eval_mode()
    return db, nnet

def Pre_load_nets():
    methods = {}
    db_cls, nnet_cls = load_net(50000, "CornerNetCls", "data/clsdata(1031)", "data/clsdata(1031)/cache",
                                "data/clsdata(1031)/result")

    from testfile.test_line_cls_pure_real import testing
    path = 'testfile.test_%s' % "CornerNetCls"
    testing_cls = importlib.import_module(path).testing
    methods['Cls'] = [db_cls, nnet_cls, testing_cls]
    db_bar, nnet_bar = load_net(50000, "CornerNetPureBar", "data/bardata(1031)", "data/bardata(1031)/cache",
                                "data/bardata(1031)/result")
    path = 'testfile.test_%s' % "CornerNetPureBar"
    testing_bar = importlib.import_module(path).testing
    methods['Bar'] = [db_bar, nnet_bar, testing_bar]
    db_pie, nnet_pie = load_net(50000, "CornerNetPurePie", "data/piedata(1008)", "data/piedata(1008)/cache",
                                "data/piedata(1008)/result")
    path = 'testfile.test_%s' % "CornerNetPurePie"
    testing_pie = importlib.import_module(path).testing
    methods['Pie'] = [db_pie, nnet_pie, testing_pie]
    db_line, nnet_line = load_net(50000, "CornerNetLine", "data/linedata(1028)", "data/linedata(1028)/cache",
                                  "data/linedata(1028)/result")
    path = 'testfile.test_%s' % "CornerNetLine"
    testing_line = importlib.import_module(path).testing
    methods['Line'] = [db_line, nnet_line, testing_line]
    db_line_cls, nnet_line_cls = load_net(20000, "CornerNetLineClsReal", "data/linedata(1028)",
                                          "data/linedata(1028)/cache",
                                          "data/linedata(1028)/result")
    path = 'testfile.test_%s' % "CornerNetLineCls"
    testing_line_cls = importlib.import_module(path).testing
    methods['LineCls'] = [db_line_cls, nnet_line_cls, testing_line_cls]
    return methods
methods = Pre_load_nets()

def ocr_result_old(image_path):
    cv_subscription_key = "xxx"
    cv_endpoint = "https://chartocr-cv.cognitiveservices.azure.com/vision/v2.1/"

    ocr_url = cv_endpoint + "recognizeText?mode=Printed"
    headers = {'Ocp-Apim-Subscription-Key': cv_subscription_key, 'Content-Type': 'application/octet-stream'}
    params = {'language': 'eng', 'detectOrientation': 'true'}

    image = Image.open(image_path)
    enh_con = ImageEnhance.Contrast(image)
    contrast = 2.0
    image = enh_con.enhance(contrast)
    # image = image.convert('L')
    # image = image.resize((800, 800))
    image.save('OCR_temp.png')
    image_data = open('OCR_temp.png', "rb").read()

    # OCR API call - need to rewrite this part
    # this call basically returns a json file with the location of the text
    response = requests.post(ocr_url, params=params, headers=headers, data=image_data)
    response.raise_for_status()

    get_url = 'https://chartocr-cv.cognitiveservices.azure.com/vision/v2.1/read/operations/'
    op_id = response.headers['apim-request-id']
    op_location = get_url + op_id
    print(op_location)
    analysis = {'status': 'Running'}
    while analysis['status'] == 'Running':
        # time.sleep(3)
        binary_content = requests.get(op_location, headers=headers, params=params).content
        analysis = json.loads(binary_content.decode('ascii'))
        print(analysis)


    line_infos = [region["lines"] for region in analysis["recognitionResults"]]
    word_infos = []
    for line in line_infos:
        for word_metadata in line:
            for word_info in word_metadata["words"]:
                if 'confidence' in word_info.keys():
                    if word_info['confidence'] == 'Low':
                        continue
                if word_info['boundingBox'][0] > word_info['boundingBox'][4]:
                    continue
                word_infos.append(word_info)
    return word_infos

def ocr_result(image_path):
    image = Image.open(image_path)
    enh_con = ImageEnhance.Contrast(image)
    contrast = 2.0
    image = enh_con.enhance(contrast)
    image = image.convert('L')
    image = image.resize((800, 800))
    image.save('OCR_temp.png')
    # image_data = open('OCR_temp.png', "rb").read()

    df_bb = pytesseract.image_to_data(image, output_type='data.frame')
    df_bb = df_bb[df_bb['conf'] != -1]
    df_bb = df_bb.drop(columns=['level', 'page_num', 'block_num', 'par_num', 'line_num', 'word_num'])
    # now we have a dataframe with the bounding box coordinates and the text
    # we need to convert this to a dictionary, with 'boundingBox' and 'text' as keys
    # the bounding box coordinates should be topleft_x, topleft_y, topright_x, topright_y, bottomright_x, bottomright_y, bottomleft_x, bottomleft_y
    # the text should be the text in the bounding box
    # build numerical array of bounding box coordinates
    df_bb['left'] = df_bb['left'].astype(int)
    df_bb['top'] = df_bb['top'].astype(int)
    df_bb['width'] = df_bb['width'].astype(int)
    df_bb['height'] = df_bb['height'].astype(int)
    df_bb['conf'] = df_bb['conf'].astype(int)
    # build bounding box coordinates array
    df_bb['boundingBox'] = df_bb.apply(
        lambda row: [row['left'], row['top'], row['left'] + row['width'], row['top'], row['left'] + row['width'],
                     row['top'] + row['height'], row['left'], row['top'] + row['height']], axis=1)
    df_bb = df_bb.drop(columns=['left', 'top', 'width', 'height', 'conf'])
    df_bb = df_bb[['boundingBox', 'text']]
    df_bb = df_bb.to_dict('records')
    return df_bb

def check_intersection(box1, box2):
    if (box1[2] - box1[0]) + ((box2[2] - box2[0])) > max(box2[2], box1[2]) - min(box2[0], box1[0]) \
            and (box1[3] - box1[1]) + ((box2[3] - box2[1])) > max(box2[3], box1[3]) - min(box2[1], box1[1]):
        Xc1 = max(box1[0], box2[0])
        Yc1 = max(box1[1], box2[1])
        Xc2 = min(box1[2], box2[2])
        Yc2 = min(box1[3], box2[3])
        intersection_area = (Xc2-Xc1)*(Yc2-Yc1)
        return intersection_area/((box2[3]-box2[1])*(box2[2]-box2[0]))
    else:
        return 0


def contains(r1, r2):
    return (r1[0] < r2[0] < r2[2] < r1[2] and r1[1] < r2[1] < r2[3] < r1[3]) or (
            r2[0] < r1[0] < r1[2] < r2[2] and r2[1] < r1[1] < r1[3] < r2[3])


# function to resize (800,800) sized bbox to fit the image
def resize_bbox(bbox, img_shape):
    size = (800, 800)

    # get the ratio of the size, y-ratio and x-ratio
    y_ratio = size[0] / img_shape[0]
    x_ratio = size[1] / img_shape[1]

    # resize the bbox
    new_bbox = []
    for i in range(len(bbox)):
        if i % 2 == 0:
            new_bbox.append(bbox[i] / x_ratio)
        else:
            new_bbox.append(bbox[i] / y_ratio)
    return new_bbox


# show bounding area of bbox from ./image.jpg, resize the bbox, key is the class
def show_bbox(classes, text_infos):
    import cv2
    img = cv2.imread('./image.jpg')
    for key in classes:
        boundingBox = [int(i) for i in classes[key]]
        cv2.rectangle(img, (int(boundingBox[0]), int(boundingBox[1])), (int(boundingBox[2]), int(boundingBox[3])),
                      (0, 0, 255), 2)
        cv2.putText(img, str(key), (int(boundingBox[0]), int(boundingBox[1])), cv2.FONT_HERSHEY_SIMPLEX, 1,
                    (0, 0, 255), 2)

    for bbox in text_infos:
        boundingBox = bbox['boundingBox']
        boundingBox = resize_bbox(boundingBox, img.shape)
        print(boundingBox, bbox['text'])
        cv2.rectangle(img, (int(boundingBox[0]), int(boundingBox[1])), (int(boundingBox[4]), int(boundingBox[5])),
                      (255, 0, 0), 2)
        cv2.putText(img, str(bbox['text']), (int(boundingBox[0]), int(boundingBox[1])), cv2.FONT_HERSHEY_SIMPLEX, 1,
                    (255, 0, 0), 2)

    plt.imshow(img)
    plt.show()


def try_math(image_path, cls_info):
    title_list = [1, 2, 3]
    title2string = {}
    x_axis_strings = []
    y_axis_strings = []

    max_value = 1
    min_value = 0
    max_y = 0
    min_y = 1
    word_infos = ocr_result(image_path)
    word_infos_ = [word_info for word_info in word_infos if word_info["text"].strip() != ""]
    print("word info ", word_infos, "\ncls info: ", cls_info)
    for id in title_list:
        if id in cls_info.keys():
            predicted_box = cls_info[id]
            words = []
            for word_info in word_infos:
                word_bbox = [word_info["boundingBox"][0], word_info["boundingBox"][1], word_info["boundingBox"][4], word_info["boundingBox"][5]]
                if check_intersection(predicted_box, word_bbox) > 0.5:
                    words.append([word_info["text"], word_bbox[0], word_bbox[1]])
            words.sort(key=lambda x: x[1]+10*x[2])
            word_string = ""
            for word in words:
                word_string = word_string + word[0] + ' '
            title2string[id] = word_string
            # get the x-axis text
    if 4 in cls_info.keys():
        predicted_box = cls_info[4]
        for word_info in word_infos_:
            bbox = word_info["boundingBox"]
            # bbox = resize_bbox(bbox, img_size) # TODO May need resize
            word_bbox = [bbox[0], bbox[1], bbox[4], bbox[5]]
            is_contain = contains(predicted_box, word_bbox)
            if is_contain:
                x_axis_strings.append(word_info["text"])

    if 5 in cls_info.keys():
        plot_area = cls_info[5]
        y_max = plot_area[1]
        y_min = plot_area[3]
        x_board = plot_area[0]
        dis_max = 10000000000000000
        dis_min = 10000000000000000
        for word_info in word_infos:
            word_bbox = [word_info["boundingBox"][0], word_info["boundingBox"][1], word_info["boundingBox"][4], word_info["boundingBox"][5]]
            word_text = word_info["text"]
            word_text = re.sub('[^-+0123456789.]', '',  word_text)
            word_text_num = re.sub('[^0123456789]', '', word_text)
            word_text_pure = re.sub('[^0123456789.]', '', word_text)
            print("processed text: ", word_text_pure)
            if len(word_text_num) > 0 and word_bbox[2] <= x_board+10:
                dis2max = math.sqrt(math.pow((word_bbox[0]+word_bbox[2])/2-x_board, 2)+math.pow((word_bbox[1]+word_bbox[3])/2-y_max, 2))
                dis2min = math.sqrt(math.pow((word_bbox[0] + word_bbox[2]) / 2 - x_board, 2) + math.pow(
                    (word_bbox[1] + word_bbox[3]) / 2 - y_min, 2))
                y_mid = (word_bbox[1]+word_bbox[3])/2
                if dis2max <= dis_max:
                    dis_max = dis2max
                    max_y = y_mid
                    max_value = float(word_text_pure)
                    if word_text[0] == '-':
                        max_value = -max_value
                if dis2min <= dis_min:
                    dis_min = dis2min
                    min_y = y_mid
                    min_value = float(word_text_pure)
                    if word_text[0] == '-':
                        min_value = -min_value
        print(min_value)
        print(max_value)
        delta_min_max = max_value-min_value
        delta_mark = min_y - max_y
        delta_plot_y = y_min - y_max
        delta = delta_min_max/delta_mark
        if abs(min_y-y_min)/delta_plot_y > 0.1:
            print(abs(min_y-y_min)/delta_plot_y)
            print("Predict the lower bar")
            min_value = int(min_value + (min_y-y_min)*delta)
    print(title2string, "---title strings")
    return title2string, round(min_value, 2), round(max_value, 2)


def test(image_path, debug=False, suffix=None, min_value_official=None, max_value_official=None):
    image_cls = Image.open(image_path)
    image = cv2.imread(image_path)
    with torch.no_grad():
        results = methods['Cls'][2](image, methods['Cls'][0], methods['Cls'][1], debug=False)
        info = results[0]
        tls = results[1]
        brs = results[2]
        plot_area = []
        image_painted, cls_info = GroupCls(image_cls, tls, brs)
        title2string, min_value, max_value = try_math(image_path, cls_info)
        if min_value_official is not None:
            min_value = min_value_official
            max_value = max_value_official
        chartinfo = [info['data_type'], cls_info, title2string, min_value, max_value]
        if info['data_type'] == 0:
            print("Predicted as BarChart")
            results = methods['Bar'][2](image, methods['Bar'][0], methods['Bar'][1], debug=False)
            tls = results[0]
            brs = results[1]
            if 5 in cls_info.keys():
                plot_area = cls_info[5][0:4]
            else:
                plot_area = [0, 0, 600, 400]
            image_painted, bar_data = GroupBar(image_painted, tls, brs, plot_area, min_value, max_value)

            return plot_area, image_painted, bar_data, chartinfo
        if info['data_type'] == 2:
            print("Predicted as PieChart")
            results = methods['Pie'][2](image, methods['Pie'][0], methods['Pie'][1], debug=False)
            print(results)
            cens = results[0]
            keys = results[1]
            image_painted, pie_data = GroupPie(image_painted, cens, keys)
            print(f"plot_area, image_painted, pie_data, chartinfo: {plot_area, image_painted, pie_data, chartinfo}")
            return plot_area, image_painted, pie_data, chartinfo
        if info['data_type'] == 1:
            print("Predicted as LineChart")
            results = methods['Line'][2](image, methods['Line'][0], methods['Line'][1], debug=False, cuda_id=1)
            keys = results[0]
            hybrids = results[1]
            if 5 in cls_info.keys():
                plot_area = cls_info[5][0:4]
            else:
                plot_area = [0, 0, 600, 400]
            print(min_value, max_value)
            image_painted, quiry, keys, hybrids = GroupQuiry(image_painted, keys, hybrids, plot_area, min_value, max_value)
            results = methods['LineCls'][2](image, methods['LineCls'][0], quiry, methods['LineCls'][1], debug=False, cuda_id=1)
            line_data = GroupLine(image_painted, keys, hybrids, plot_area, results, min_value, max_value)
            return plot_area, image_painted, line_data, chartinfo





if __name__ == "__main__":

    tar_path = 'C:/work/clsdata(1031)/cls/images/test2019'
    images = os.listdir(tar_path)
    from random import shuffle
    shuffle(images)
    for image in tqdm(images):
        path = os.path.join(tar_path, image)
        test(path)

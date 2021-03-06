# encoding=utf-8

"""
    处理图片背景
"""

import os
import re
import traceback
import contextlib
import ImageFilter
import ImageEnhance
from PIL import Image
from math import log


class NewImage:
    def __init__(self, file_name, file_path=None):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.img_file_dir = os.path.join(self.base_dir, file_path) if file_path else os.path.join(self.base_dir, u'script\images')
        self.file_dir = os.path.join(self.img_file_dir, file_name)
        self.im = Image.open(self.file_dir)


@contextlib.contextmanager
def open_image(file_name, file_path=None):
    new_im = NewImage(file_name, file_path)
    try:
        yield new_im
    except Exception as e:
        print e
    finally:
        pass


def get_average_image_color(img_name):
    try:
        with open_image(img_name) as image:
            new_img = image.im
            width, height = new_img.size
            r, g, b = new_img.split()
            alpha = b
            main_alpha = alpha.getdata()
            main_color = main_alpha[0]
            color_dict = dict()
            # 扫描一个通道的色值
            for h in range(height):
                for w in range(width):
                    pixel = alpha.getpixel((w, h))
                    if pixel not in color_dict:
                        color_dict[pixel] = 0
                    else:
                        color_dict[pixel] += 1
            value = 0
            for k, v in color_dict.items():
                value += k*v
            alw = (main_color - value / (width * height))
            print main_color
            print value / (width * height)
            return alw
    except Exception as e:
        print e


def get_average_area_color(img_name, path=None):
    try:
        with open_image(img_name, path) as image:
            new_img = image.im
            width, height = new_img.size
            r, g, b = new_img.split()
            alpha = b
            main_alpha = alpha.getdata()
            main_color = main_alpha[0]
            area_color_info = dict()
            # 扫描主区域
            for h in range(height):
                # 是否进入素材
                is_area = False
                for w in range(width):
                    pixel = alpha.getpixel((w, h))
                    # 进入素材
                    if pixel < main_color - 20:
                        if not is_area:
                            if pixel not in area_color_info:
                                # 记录边界值
                                area_color_info[pixel] = 1
                            else:
                                area_color_info[pixel] += 1
                            is_area = True
                    # 离开素材
                    if is_area:
                        if pixel >= main_color - 5:
                            pixel = alpha.getpixel((w-1, h))
                            if pixel not in area_color_info:
                                area_color_info[pixel] = 1
                            else:
                                area_color_info[pixel] += 1
                            is_area = False
            value = 0
            all_count = 0
            area_alw_info = list()
            for k, v in area_color_info.items():
                value += k * v
                all_count += v
                area_alw_info.append(k)
            alw = main_color - sorted(area_alw_info)[-1]
            return alw
    except Exception as e:
        print traceback.format_exc(e)


# 通过转换为灰度的方式获取区域
def get_average_area_color_rgb(img_name):
    try:
        with open_image(img_name) as image:
            new_img = image.im
            width, height = new_img.size
            main_color = sum(new_img.getpixel((0, 0)))
            area_color_info = dict()
            for h in range(height):
                is_area = False
                for w in range(width):
                    pixel = sum(new_img.getpixel((w, h)))
                    # 进入素材
                    if pixel < main_color:
                        if not is_area:
                            if pixel not in area_color_info:
                                # 记录边界值
                                area_color_info[pixel] = 1
                            else:
                                area_color_info[pixel] += 1
                            is_area = True
                    # 离开素材
                    if is_area:
                        if pixel >= main_color:
                            pixel = sum(new_img.getpixel((w - 1, h)))
                            if pixel not in area_color_info:
                                area_color_info[pixel] = 1
                            else:
                                area_color_info[pixel] += 1
                            is_area = False
            value = 0
            all_count = 0
            area_alw_info = list()
            for k, v in area_color_info.items():
                value += k * v
                all_count += v
                area_alw_info.append(k)
                print k, v
            area_color_info = sorted(area_color_info.items(), key=lambda x: x[1], reverse=True)
            alw = main_color - area_alw_info[0][0]
            return alw
    except Exception as e:
        print traceback.format_exc(e)


# 通过色彩范围分析
def get_color_area_image(img_name):
    try:
        with open_image(img_name) as image:
            new_img = image.im
            width, height = new_img.size
            alpha = new_img.convert('L')
            alw = 5
            main_color = sum(new_img.getpixel((0, 0))) - alw
            for h in range(height):
                for w in range(width):
                    pixel = sum(new_img.getpixel((w, h)))
                    # 需要剔除的部分
                    if pixel >= main_color:
                        alpha.putpixel((w, h), 0)
                    else:
                        alpha.putpixel((w, h), 255)
            # 重新分解通道
            r, g, b = new_img.split()
            a_img = Image.merge('RGBA', (r, g, b, alpha))
            name = img_name.split('.')[0] + '_color_area'
            t = 'png'
            new_name = '.'.join([name, t])
            a_img.save(new_name)
    except Exception as e:
        print traceback.format_exc(e)


# 不适合素材中要保留的部分颜色接近背景色
def get_area_image(img_name, alw=None, ecl=5, path=None):
    try:
        with open_image(img_name, path) as image:
            if not alw:
                alw = get_average_area_color(img_name, path)
            print 'alw: %s' % alw
            new_img = image.im
            width, height = new_img.size
            r, g, b = new_img.split()
            alpha = b
            main_alpha = alpha.getdata()
            main_color = main_alpha[0]
            # 扫描主区域
            for h in range(height):
                row_info = list()
                row_info.append(0)
                # 是否进入素材
                is_area = False
                for w in range(width):
                    pixel = alpha.getpixel((w, h))
                    # 进入素材
                    if pixel < main_color - alw:
                        if not is_area:
                            row_info.append(w)
                            is_area = True
                    # 离开素材
                    if is_area:
                        if pixel >= main_color - alw:
                            row_info.append(w)
                            is_area = False
                row_info.append(width)
                # 是否进入素材
                is_a = False
                for row_area_i in range(len(row_info) - 1):
                    for row_area in range(row_info[row_area_i], row_info[row_area_i+1]):
                        if not is_a:
                            alpha.putpixel((row_area, h), 0)
                        if is_a:
                            # cap = row_area - row_info[row_area_i]
                            # _cap = row_info[row_area_i + 1] - row_area
                            # if cap < ecl:
                            #     a = int(255 * 0.9 / pow(2, ecl-1) * (pow(2, cap) - 1))
                            #     alpha.putpixel((row_area, h), a)
                            # elif _cap < ecl:
                            #     a = int(255 * 0.9 / pow(2, ecl - 1) * (pow(2, _cap) - 1))
                            #     alpha.putpixel((row_area, h), a)
                            # else:
                            alpha.putpixel((row_area, h), 255)
                    is_a = not is_a
            # 重新分解通道
            r, g, b = new_img.split()
            a_img = Image.merge('RGBA', (r, g, b, alpha))
            name = 'new_' + img_name.split('.')[0]
            t = 'png'
            new_name = '.'.join([name, t])
            a_img.save(new_name)
    except Exception as e:
        print traceback.format_exc(e)


# 批量处理图片
def batch_handler_image(file_path):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    full_file_path = os.path.join(base_dir, file_path)
    if os.path.exists(full_file_path):
        for s in os.listdir(full_file_path):
            file_format = s.split('.')[-1]
            if file_format.upper() == 'JPG':
                print u'当前处理图片: %s' % s
                get_area_image(s, alw=15, path=file_path)


if __name__ == '__main__':
    # get_area_image('test_8.jpg', alw=5)
    batch_handler_image(u'script\get_image_scripts\火焰')


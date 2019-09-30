# -*- coding: utf-8 -*-
import os
import cv2
import base64
import numpy as np
from keras import models
from captcha.texts import texts

_file_path = os.path.dirname(__file__)
model_text = models.load_model(os.path.abspath(os.path.join(_file_path, 'models/model.v2.0.h5')))
model_image = models.load_model(os.path.abspath(os.path.join(_file_path, 'models/12306.image.model.h5')))


class CaptchaImage:
    """
    验证码图片
    """
    def __init__(self, image64):
        """
        :param image64: base64编码
        """
        self.captcha = self.base64_to_image(image64)
        self.text = self._get_text()
        self.images = self._get_images()

    def bypass(self):
        # 八张图对应的坐标
        coordinates = [
            ('40', '50'), ('120', '50'), ('180', '50'), ('250', '50'),
            ('40', '120'), ('120', '120'), ('180', '120'), ('250', '120')
        ]
        answer = []
        for index, img in enumerate(self.images):
            if img in self.text:
                answer += coordinates[index]
        answer = ','.join(answer)
        return answer

    @staticmethod
    def base64_to_image(base64_str):
        """
        将图片的base64编码转为cv识别的ndarray
        :param base64_str: 图片的base64编码
        :return: cv图片
        """
        img_bytes = base64.b64decode(base64_str)
        img_array = np.frombuffer(img_bytes, np.uint8)
        image = cv2.imdecode(img_array, cv2.COLOR_RGB2BGR)
        return image

    def _get_text(self, offset=0):
        """
        识别文字内容
        :param offset: 文字位置偏移量
        """
        # 预处理
        text = self.captcha[3: 22, offset + 120: offset + 177]
        text = cv2.cvtColor(text, cv2.COLOR_BGR2GRAY)
        text = text / 255.0
        h, w = text.shape
        text.shape = (1, h, w, 1)

        if offset == 0:
            label = model_text.predict(text)
            label = label.argmax()
            text = texts[label]

            # 根据第一个词语的字数确定第二个词语的位置偏移量
            offset = [27, 47, 60][len(text) - 1]
            text2 = self._get_text(offset)
            if text2:
                return [text, text2]
            else:
                return [text]

        else:
            # 如果不是全白，则第二个词语存在
            if text.mean() < 0.95:
                label = model_text.predict(text)
                label = label.argmax()
                return texts[label]
            else:
                return

    def _get_images(self):
        """
        识别图片内容
        """
        images = self._cut_images()

        # 预处理
        images = np.array(images)
        images = images.astype('float32')
        mean = [103.939, 116.779, 123.68]
        images -= mean

        labels = model_image.predict(images)
        labels = labels.argmax(axis=1)
        images = [texts[i] for i in labels]
        return images

    def _cut_images(self):
        """
        切割八张图片
        """
        height, width, _ = self.captcha.shape
        gap = 5
        unit = 67
        images = []
        for x in range(40, height - unit, gap + unit):
            for y in range(gap, width - unit, gap + unit):
                images.append(self.captcha[x: x + unit, y: y + unit])
        return images


def test():
    with open('test_img.txt', 'r') as f:
        img64 = f.read()
    captcha = CaptchaImage(img64)

    print(captcha.text)
    print(captcha.images)
    print(captcha.bypass())

    cv2.imshow('验证码', captcha.captcha)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == '__main__':
    test()

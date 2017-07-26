import base64
import logging
from logging import Logger
import os
import re
import time
from typing import List
import urllib.request

from bs4 import BeautifulSoup
import boto3
import click
import requests
from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver as ChromeDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import StaleElementReferenceException

from PIL import ImageGrab, Image
import pickle

from dynamo import DynamoClient
from jins_entity import GlassProduct
from local_io import FileChecker


JINS_COOKIE_PATH = "cookie_storage/cookies.pkl"
JINS_BASE_URL = "https://www.jins.com/jp/"

JINS_DETAIL_PATH_TEMPLATE = "https://www.jins.com/jp/Products/Detail/number/{product_id}/{color_no}/?from_search=1"


class JinsScraper:
    def __init__(self, save_dir: str, log_dir: str, is_virtual: bool=True, auth_url:str=""):
        self.log_dir = log_dir
        self.logger: Logger = self.create_logger()
        self.driver: ChromeDriver = self.create_driver()
        self.save_dir = save_dir
        self.is_virtual = is_virtual
        self.auth_url = auth_url
        self.dynamo = DynamoClient()
        self.file_checker = FileChecker(save_dir)

    def create_logger(self) -> logging.Logger:
        logger = logging.getLogger("JVFR")
        if self.log_dir[-1] != '/':
            self.log_dir += '/'
        fh = logging.FileHandler(self.log_dir + 'jins.log', 'a+')
        formatter = logging.Formatter('[%(asctime)s] %(message)s')
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        logger.setLevel(logging.INFO)
        return logger


    def create_driver(self) -> ChromeDriver:
        chrome_options = webdriver.ChromeOptions()
        prefs = {"profile.default_content_setting_values.notifications": 2}
        chrome_options.add_experimental_option("prefs", prefs)
        driver = webdriver.Chrome(chrome_options=chrome_options)
        driver.set_page_load_timeout(20)
        driver.implicitly_wait(30)
        return driver

    # 認証ページへ行く. faceNoは自動入力. facePasswordはこのコードで自動入力する. その後10秒間待機するので、その間に人力で画像キャプチャ認証を行う.
    def auth_through(self):
        self.driver.get(self.auth_url)
        self.driver.maximize_window()
        # driver.find_element_by_id("faceNo").send_keys("928227719")
        self.driver.find_element_by_id("facePassword").send_keys("olab1")

        # この間に画像認証をやる
        time.sleep(10)

        # 認証ボタンクリック
        auth_span = self.driver.find_element_by_id(
            "auth_wrapper").find_element_by_xpath('.//span[text()="認証"]')
        auth_span.find_element_by_xpath("../..").click()

        # cookieを保存
        save_cookies(self.driver)

    def get_canvas(self):
        try_count = 0
        while True:
            try:
                canvas: WebElement = WebDriverWait(self.driver, 60).until(find_canvas)
                if canvas:
                    return canvas
                else:
                    if try_count > 5:
                        return None
                    try_count += 1
                    time.sleep(1)
            except Exception as e:
                if try_count > 5:
                    return None
                time.sleep(1)
                try_count += 1

    # 商品ページからバーチャルメガネ画像を保存する
    def save_virtual_fit_image(self, product_id, color_no):
        try:
            canvas: WebElement = self.get_canvas()
            offset_x = canvas.size['width'] / 12
            for i in range(-6, 7, 1):
                if i == 0:
                    webdriver.ActionChains(self.driver).context_click(canvas).perform()
                else:
                    bias = - signed(i) * (offset_x / 2)
                    webdriver.ActionChains(self.driver).move_to_element(canvas).move_by_offset(
                        offset_x * i + bias, 0).click().context_click().perform()

                filename = create_filename(self.save_dir, product_id, color_no, i)
                self.save_context_clicked_image(filename, is_virtualfit=True)
                self.logger.info('name:%s', filename)
                print(filename)
        except StaleElementReferenceException as e:
            self.logger.error(e)

    def save_non_virtual_fit_image(self, product_id, color_no):
        img = self.driver.find_element_by_id("product_main_image_inner").find_element_by_tag_name("img")
        webdriver.ActionChains(self.driver).context_click(img).perform()

        filename = create_filename(self.save_dir, product_id, color_no, 94)
        self.save_context_clicked_image(filename, is_virtualfit=False)
        self.logger.info('name:%s', filename)
        print(filename)

    def access_glass_detail_page(self, product_id, color_no):
        url = JINS_DETAIL_PATH_TEMPLATE.format(product_id=product_id,
                                               color_no=color_no)
        print(url)
        self.driver.get(url)
        popup_enter()
        time.sleep(3)

    def scrape_color_name(self):
        try:
            color_id_and_name = self.driver.find_element_by_id("colorName").text
            color_id_and_name = re.sub(r'\s|\n', '', color_id_and_name)
            id_name = color_id_and_name.split(':')
            color_id = id_name[0]
            color_name = id_name[1]
            self.dynamo.put_color(color_id, color_name)
            print(color_id, color_name)
        except Exception as e:
            self.logger.error(e)

    def click_virtualfit(self):
        vf_checkbox = self.driver.find_element_by_id("vtoCheck")
        if not vf_checkbox.is_selected():
            self.driver.find_element_by_id("vtoCheckLabel").click()
            time.sleep(5)

    def scrape_items(self):
        if self.is_virtual:
            self.auth_through()
        items = self.dynamo.get_products()

        for item in items:
            product_id = item["ProductID"]
            for color_no in item["Colors"]:
                # ファイル存在チェック
                is_exist = self.file_checker.isExist(product_id, color_no)
                if is_exist:
                    continue

                try:
                    # 商品ページにアクセス
                    self.access_glass_detail_page(product_id, color_no)

                    # カラー番号
                    self.scrape_color_name()

                    if self.is_virtual:
                        # バーチャルフィットチェックボタンクリック
                        self.click_virtualfit()
                        time.sleep(3)
                        # 右クリックして、画像保存
                        self.save_virtual_fit_image(product_id, color_no)
                    else:
                        self.save_non_virtual_fit_image(product_id, color_no)
                except Exception as e:
                    self.logger.error("{}".format(e))

    def save_canvas_binary(self, canvas: WebElement, filename: str):
        # get the canvas as a PNG base64 string
        canvas_base64 = self.driver.execute_script(
            "return arguments[0].toDataURL('image/png').substring(21);", canvas)
        # canvas_base64 = driver.execute_script("return arguments[0].toDataURL('image/png');", canvas)
        time.sleep(5)
        # decode
        canvas_png = base64.b64decode(canvas_base64)
        # save to a file
        with open(filename, 'wb') as f:
            f.write(canvas_png)

    def save_context_clicked_image(self, filename: str, is_virtualfit: bool):
        # cmd_active_context_menu = """
        #     osascript -e 'tell application "System Events" to keystroke "v"'
        #     """
        # os.system(cmd_active_context_menu)
        # time.sleep(1)

        # press arrow down and select copy image
        cmd_select_copy_image = """
            osascript -e 'tell application "System Events" to key code 125'
        """
        os.system(cmd_select_copy_image)
        os.system(cmd_select_copy_image)

        if not is_virtualfit:
            os.system(cmd_select_copy_image)

        # press enter and copy image to clipboard
        cmd_press_enter = """
            osascript -e 'tell application "System Events" to key code 36'
        """
        os.system(cmd_press_enter)
        time.sleep(0.1)

        im = ImageGrab.grabclipboard()
        if isinstance(im, Image.Image):
            im.save(filename)
            print('saved')
        else:
            print('no image')


    def find_product_list(self):
        products = self.driver.find_element_by_id(
            "asyncSearchResultView").find_elements_by_class_name('asyncProductWrapper')
        if products:
            return products
        else:
            return False



    def find_color_img(self, c: WebElement):
        img = c.find_element_by_tag_name('a').find_element_by_tag_name('img')
        if img:
            return img
        else:
            return False

    def check_exists_canvas(self):
        try:
            self.driver.find_element_by_id("vto").find_element_by_tag_name('canvas')
        except NoSuchElementException:
            return False
        return True


def find_canvas(driver: ChromeDriver):
    canvas = driver.find_element_by_id("vto").find_element_by_tag_name('canvas')
    if canvas:
        return canvas
    else:
        return False


def create_jins_db(driver: ChromeDriver):

    dynamo_client = DynamoClient()
    page = 1
    while True:
        url = 'https://www.jins.com/jp/Search/All/1/?jcas=1#/Search/json?category=1&keyword=&page=' + str(page) + '&sort=3&angle=shomen'
        driver.get(url)
        data = driver.page_source.encode("utf-8")
        soup = BeautifulSoup(data, 'html.parser')
        pro_list = soup.find_all(class_="asyncProductInner")
        print(len(pro_list))
        num_page_products = len(pro_list)
        if num_page_products < 1:
            break

        products: list[GlassProduct] = []
        for p in pro_list:
            product_id = p.get("katacd")
            print(p.get("katacd"))

            glass_product = GlassProduct(product_id)
            color_list = p.find('ul', {"class": "colors"})
            for c in color_list.find_all('li'):
                color_id = c.get("color")
                print(color_id)
                glass_product.add_color(color_id)

            products.append(glass_product)

        dynamo_client.put_products(products, page)
        print(page)
        page += 1
        time.sleep(3)


def load_save_dir_filenames(save_dir: str):
    pass


def create_filename(dir_name:str, product_id: str, color_no: str, angle_id: int):
    if dir_name[-1] != '/':
        dir_name += '/'
    return dir_name + product_id + "_" + color_no + "_" + str(angle_id+6) + ".png"


AUTH_URL = "https://www.jins-jp.com/VirtualFit/Auth?fn=b13c066b4b0229b2c8c74f3d29afc18d81ea6b7435c630af5a59f81154dddc8f"


def signed(i: int):
    if i < 0:
        return -1
    if i >= 0:
        return 1


def save_srcimg(src: str, filename: str):
    image_name = src.split('/')[-1]
    urllib.request.urlretrieve(src, filename)


def popup_enter():
    # press enter and copy image to clipboard
    cmd_press_enter = """
            osascript -e 'tell application "System Events" to key code 36'
        """
    os.system(cmd_press_enter)

def save_cookies(driver: ChromeDriver):
    pickle.dump(driver.get_cookies(), open(JINS_COOKIE_PATH, "wb"))


def load_cookies(driver: ChromeDriver):
    cookies = pickle.load(open(JINS_COOKIE_PATH, "rb"))
    for cookie in cookies:
        driver.add_cookie(cookie)

@click.group()
def cmd():
    pass

@cmd.command()
def create_db(prefix):
    print("create_db")
    print(prefix)


@cmd.command()
@click.option('--virtual/--no-virtual', default=True, help="Virtual Fit or Not")
@click.option('--auth_url', default='hello', help="Auth URL.")
@click.option('--save_dir', default='hello', help='Save dir name')
@click.option('--log_dir', default='hello', help='Log dir name')
def scrape(virtual, auth_url, save_dir, log_dir):
    if virtual and auth_url == 'hello':
        print('Please specify --auth_url if virtual.')
        return
    if save_dir == 'hello':
        print('Please specify --save_dir.')
    if log_dir == 'hello':
        print('Please specify --log_dir.')

    scraper = JinsScraper(
                save_dir=save_dir,
                log_dir=log_dir,
                is_virtual=virtual,
                auth_url=auth_url)
    scraper.scrape_items()


if __name__ == '__main__':
    cmd()

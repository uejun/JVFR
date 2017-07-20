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


JINS_COOKIE_PATH = "cookie_storage/cookies.pkl"
JINS_BASE_URL = "https://www.jins.com/jp/"

JINS_DETAIL_PATH_TEMPLATE = "https://www.jins.com/jp/Products/Detail/number/{product_id}/{color_no}/?from_search=1"


class GlassProduct:

    def __init__(self, product_id: str):
        self.product_id: str = product_id
        self.color_list: list[str] = []

    def add_color(self, color_id: str):
        self.color_list.append(color_id)

    def create_detail_page_href(self, color_id):
        return "https://www.jins.com/jp/Products/Detail/number/" + self.product_id + "/" + color_id + "/?from_search=1"


class DynamoClient:

    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb', region_name='ap-northeast-1')
        self.table = self.dynamodb.Table("jvfr_glass")
        self.color_table = self.dynamodb.Table("jvfr_color")
        if self.table == None:
            raise Exception("table is None.")


    def put_product(self, product: GlassProduct, page_num: int):
        response = self.table.put_item(
            Item={
                'ProductID': product.product_id,
                'PageNum': page_num,
                'Colors': product.color_list
            }
        )

    def put_products(self, products, page_num: int):
        for product in products:
            self.put_product(product, page_num)

    def get_products(self):
        res = self.table.scan(Limit=2)
        return res["Items"]

    def put_color(self, color_id, color_name):
        response = self.color_table.put_item(
            Item={
                'color_id': color_id,
                'color_name': color_name
            }
        )

def create_logger() -> logging.Logger:
    logger = logging.getLogger("JVFR")
    fh = logging.FileHandler('/Users/uejun/Desktop/logs/jins.log', 'a+')
    formatter = logging.Formatter('[%(asctime)s] %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    logger.setLevel(logging.INFO)
    return logger


def create_driver() -> ChromeDriver:
    chrome_options = webdriver.ChromeOptions()
    prefs = {"profile.default_content_setting_values.notifications": 2}
    chrome_options.add_experimental_option("prefs", prefs)
    driver = webdriver.Chrome(chrome_options=chrome_options)
    driver.set_page_load_timeout(20)
    driver.implicitly_wait(30)
    return driver


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



#認証ページへ行く. faceNoは自動入力. facePasswordはこのコードで自動入力する. その後10秒間待機するので、その間に人力で画像キャプチャ認証を行う.
def auth_through(driver: ChromeDriver, url: str):

    driver.get(url)
    driver.maximize_window()
    # driver.find_element_by_id("faceNo").send_keys("928227719")
    driver.find_element_by_id("facePassword").send_keys("olab1")

    # この間に画像認証をやる
    time.sleep(10)

    # 認証ボタンクリック
    auth_span = driver.find_element_by_id(
        "auth_wrapper").find_element_by_xpath('.//span[text()="認証"]')
    auth_span.find_element_by_xpath("../..").click()

    # cookieを保存
    save_cookies(driver)


# 商品ページからバーチャルメガネ画像を保存する
def save_virtual_fit_image(driver: ChromeDriver, logger: Logger, product_id, color_no, save_dir):
    try:
        canvas: WebElement = WebDriverWait(driver, 60).until(find_canvas)
        offset_x = canvas.size['width'] / 12
        for i in range(-6, 7, 1):
            if i == 0:
                webdriver.ActionChains(driver).context_click(canvas).perform()
            else:
                bias = - signed(i) * (offset_x / 2)
                webdriver.ActionChains(driver).move_to_element(canvas).move_by_offset(
                    offset_x * i + bias, 0).click().context_click().perform()

            filename = create_filename(save_dir, product_id, color_no, i)
            save_context_clicked_image(filename, is_virtualfit=True)
            logger.info('name:%s', filename)
            print(filename)
    except StaleElementReferenceException as e:
        logger.error(e)


def save_non_virtual_fit_image(driver: ChromeDriver, logger: Logger, product_id, color_no, save_dir):
    img = driver.find_element_by_id("product_main_image_inner").find_element_by_tag_name("img")
    webdriver.ActionChains(driver).context_click(img).perform()

    filename = create_filename(save_dir, product_id, color_no, 94)
    save_context_clicked_image(filename, is_virtualfit=False)
    logger.info('name:%s', filename)
    print(filename)


def create_filename(dir_name:str, product_id: str, color_no: str, angle_id: int):
    if dir_name[-1] != '/':
        dir_name += '/'
    return dir_name + product_id + "_" + color_no + "_" + str(angle_id+6) + ".png"

def access_glass_detail_page(driver: ChromeDriver, product_id, color_no):
    url = JINS_DETAIL_PATH_TEMPLATE.format(product_id=product_id,
                                           color_no=color_no)
    print(url)
    time.sleep(3)
    driver.get(url)
    popup_enter()
    time.sleep(3)

def scrape_color_name(driver: ChromeDriver, dynamo: DynamoClient):
    color_id_and_name = driver.find_element_by_id("colorName").text
    color_id_and_name = re.sub(r'\s|\n', '', color_id_and_name)
    id_name = color_id_and_name.split(':')
    color_id = id_name[0]
    color_name = id_name[1]
    dynamo.put_color(color_id, color_name)
    print(color_id, color_name)

def click_virtualfit(driver: ChromeDriver):
    vf_checkbox = driver.find_element_by_id("vtoCheck")
    if not vf_checkbox.is_selected():
        driver.find_element_by_id("vtoCheckLabel").click()
        time.sleep(5)

def scrapy_items(driver: ChromeDriver, logger: Logger, items: list, save_dir: str, dynamo, is_virtualfit: bool = True):
    for item in items:
        product_id = item["ProductID"]
        for color_no in item["Colors"]:
            # 商品ページにアクセス
            access_glass_detail_page(driver, product_id, color_no)

            # カラー番号
            scrape_color_name(driver, dynamo)

            if is_virtualfit:
                # バーチャルフィットチェックボタンクリック
                click_virtualfit(driver)

                # 右クリックして、画像保存
                save_virtual_fit_image(driver, logger, product_id, color_no, save_dir)

            else:
                save_non_virtual_fit_image(driver, logger, product_id, color_no, save_dir)

AUTH_URL = "https://www.jins-jp.com/VirtualFit/Auth?fn=b13c066b4b0229b2c8c74f3d29afc18d81ea6b7435c630af5a59f81154dddc8f"

def scrape_glass_images_directly(driver: ChromeDriver, logger: Logger, save_dir: str, is_virtualfit: bool):
    if is_virtualfit:
        auth_through(driver, AUTH_URL)
    dynamo_client = DynamoClient()
    items = dynamo_client.get_products()
    scrapy_items(driver, logger, items, save_dir, dynamo_client, is_virtualfit)


def access(driver: ChromeDriver, logger: Logger, is_virtualfit: bool, is_auth: bool, start_page=0, start_idx=0):

    dir_name = "/Users/uejun/Desktop/downloads/"

    if is_virtualfit:
        # 認証あり
        if is_auth:
            url = "https://www.jins-jp.com/VirtualFit/Auth?fn=b13c066b4b0229b2c8c74f3d29afc18d81ea6b7435c630af5a59f81154dddc8f"
            driver.get(url)
            driver.maximize_window()
            # driver.find_element_by_id("faceNo").send_keys("928227719")
            driver.find_element_by_id("facePassword").send_keys("olab1")

            # この間に画像認証をやる
            time.sleep(10)

            # 認証ボタンクリック
            auth_span = driver.find_element_by_id(
                "auth_wrapper").find_element_by_xpath('.//span[text()="認証"]')
            auth_span.find_element_by_xpath("../..").click()

            # cookieを保存
            save_cookies(driver)

        else:
            # 認証なし
            url = "https://www.jins.com/jp/"
            driver.get(url)
            driver.maximize_window()
            load_cookies(driver)

    else:
        url = "https://www.jins.com/jp/"
        driver.get(url)
        driver.maximize_window()



    # 商品一覧ページのスタートのページナンバー
    page = start_page
    saved_count: int = 0
    while True:
        logger.info('page:%s', page)
        driver.get(
            f'https://www.jins.com/jp/Search/All/1/?jcas=1#/Search/json?category=1&keyword=&page={page}&sort=3&angle=shomen')

        time.sleep(3)

        # 商品一覧を取得
        # products_per_page: List[webdriver.remote.webelement.WebElement] = driver.find_element_by_id(
        #     "asyncSearchResultView").find_elements_by_class_name('asyncProductWrapper')

        products_per_page: list[WebElement] = WebDriverWait(driver, 60).until(find_product_list)
        num_per_page = len(products_per_page)

        logger.info('product_counts:%s', num_per_page)
        print('商品数' + str(num_per_page))

        if num_per_page < 1:
            break

        hrefs: list[str] = []
        product_ids: list[str] = []
        products: list[GlassProduct] = []
        for product_elem in products_per_page:
            link: WebElement = product_elem.find_element_by_class_name(
                "asyncProductImage").find_element_by_tag_name('a')
            href = link.get_attribute("href")

            # 品番の取得
            product_id = href.split('/')[-3]
            print(product_id)
            product_ids.append(product_id)
            hrefs.append(link.get_attribute("href"))

            # GlassProductの生成
            glass_product = GlassProduct(product_id)

            # カラーIDの取得・追加
            colors_clearfix: WebElement = product_elem.find_element_by_class_name('colors')
            color_list: list[WebElement] =  colors_clearfix.find_elements_by_tag_name("li")
            for celem in color_list:

                color_id = celem.get_attribute("color")
                print(color_id)
                glass_product.add_color(color_id)

            # GlassProductのリスト追加
            products.append(glass_product)

        current_num_in_current_page: int = start_idx
        while current_num_in_current_page < len(products_per_page):
            product_elem = products[current_num_in_current_page]
            logger.info('{%s}/{%s}/page%s', current_num_in_current_page, num_per_page, page)

            for color_id in product_elem.color_list:
                href = product_elem.create_detail_page_href(color_id)
                driver.get(href)

                # バーチャルフィットチェックボタンクリック
                if is_virtualfit:
                    vf_checkbox = driver.find_element_by_id("vtoCheck")
                    if not vf_checkbox.is_selected():
                        driver.find_element_by_id("vtoCheckLabel").click()
                        time.sleep(5)

                color_name = driver.find_element_by_id('dtlColor').text

                if is_virtualfit:
                    try:
                        canvas: WebElement = WebDriverWait(driver, 60).until(find_canvas)
                        offset_x = canvas.size['width'] / 12
                        for i in range(-6, 7, 1):
                            if i == 0:
                                webdriver.ActionChains(driver).context_click(canvas).perform()
                            else:
                                bias = - signed(i) * (offset_x / 2)
                                webdriver.ActionChains(driver).move_to_element(canvas).move_by_offset(
                                    offset_x * i + bias, 0).click().context_click().perform()

                            product_color_name = product_elem.product_id + "-" + color_id + "_" + str(i+6)
                            filename = dir_name + product_color_name + ".png"

                            save_context_clicked_image(filename, is_virtualfit)
                            saved_count += 1

                            logger.info('name:%s', product_color_name)
                            print(product_color_name)
                            logger.info('current_count:%s', saved_count)
                    except StaleElementReferenceException as e:
                        logger.error(e)
                else:
                    # img_src: str = driver.find_element_by_id("product_main_image_inner").find_element_by_tag_name("img").get_attribute('src')
                    img = driver.find_element_by_id(
                        "product_main_image_inner").find_element_by_tag_name("img")
                    webdriver.ActionChains(driver).context_click(img).perform()

                    product_color_name = product_elem.product_id + "-" + color_id + "_glass"
                    filename = dir_name + product_color_name + ".png"

                    save_context_clicked_image(filename, is_virtualfit)
                    saved_count += 1

                    logger.info('name:%s', product_color_name)
                    print(product_color_name)
                    logger.info('current_count:%s', saved_count)



            current_num_in_current_page += 1
        page += 1


def find_product_list(driver: ChromeDriver):
    products = driver.find_element_by_id(
        "asyncSearchResultView").find_elements_by_class_name('asyncProductWrapper')
    if products:
        return products
    else:
        return False


def find_canvas(driver: ChromeDriver):
    canvas = driver.find_element_by_id("vto").find_element_by_tag_name('canvas')
    if canvas:
        return canvas
    else:
        return False

def find_color_img(c: WebElement):
    img = c.find_element_by_tag_name('a').find_element_by_tag_name('img')
    if img:
        return img
    else:
        return False

def signed(i: int):
    if i < 0:
        return -1
    if i >= 0:
        return 1


def save_srcimg(src: str, filename: str):
    image_name = src.split('/')[-1]
    urllib.request.urlretrieve(src, filename)


def save_canvas_binary(driver: ChromeDriver, canvas: WebElement, filename: str):
        # get the canvas as a PNG base64 string
    canvas_base64 = driver.execute_script(
        "return arguments[0].toDataURL('image/png').substring(21);", canvas)
    # canvas_base64 = driver.execute_script("return arguments[0].toDataURL('image/png');", canvas)
    time.sleep(5)
    # decode
    canvas_png = base64.b64decode(canvas_base64)
    # save to a file
    with open(filename, 'wb') as f:
        f.write(canvas_png)


def save_context_clicked_image(filename: str, is_virtualfit: bool):
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
    time.sleep(3)

    im = ImageGrab.grabclipboard()
    if isinstance(im, Image.Image):
        im.save(filename)
        print('saved')
    else:
        print('no image')

# driver.close()

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


def check_exists_canvas(driver: ChromeDriver):
    try:
        driver.find_element_by_id("vto").find_element_by_tag_name('canvas')
    except NoSuchElementException:
        return False
    return True

# @click.command()
# @click.option('--page', type=int, default=1)
# @click.option('--idx', type=int, default=1)
def do(page, idx):
    logger = create_logger()
    driver = create_driver()
    access(driver, logger, is_virtualfit=False, is_auth=False, start_page=page, start_idx=idx)

@click.group()
def cmd():
    pass

@cmd.command()
def create_db():
    print("create_db")
    driver = create_driver()
    create_jins_db(driver)

@cmd.command()
def crawl_save():
    driver = create_driver()
    logger = create_logger()
    save_dir = "/Users/uejun/Desktop/dev"
    scrape_glass_images_directly(driver, logger, save_dir, is_virtualfit=False)
    print("crawl_save")

def main():
    cmd()

if __name__ == '__main__':
    main()

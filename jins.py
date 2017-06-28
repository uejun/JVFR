import base64
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver as ChromeDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException
import urllib.request
from typing import List
from PIL import ImageGrab, Image
import pickle

JINS_COOKIE_PATH = "cookie_storage/cookies.pkl"


def create_driver() -> ChromeDriver:
    chrome_options = webdriver.ChromeOptions()
    prefs = {"profile.default_content_setting_values.notifications" : 2}
    chrome_options.add_experimental_option("prefs",prefs)
    driver = webdriver.Chrome(chrome_options=chrome_options)
    driver.set_page_load_timeout(20)
    driver.implicitly_wait(10)
    return driver


def access(driver: ChromeDriver, is_virtualfit: bool, is_auth: bool):
    if is_virtualfit:
        # 認証あり
        if is_auth:
            url = "https://www.jins-jp.com/VirtualFit/Auth?fn=093ec84994522398fc473b49dd910b6ee0c9c596424e1c3192fa210210196e2c"
            driver.get(url)
            driver.maximize_window()
            # driver.find_element_by_id("faceNo").send_keys("928227719")
            driver.find_element_by_id("facePassword").send_keys("olab1")

            # この間に画像認証をやる
            time.sleep(10)

            # 認証ボタンクリック
            auth_span = driver.find_element_by_id("auth_wrapper").find_element_by_xpath('.//span[text()="認証"]')
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

    # 上のメニュー項目の商品検索をクリック
    # submenu = driver.find_element_by_id("subMenu-container")
    # submenu.find_element_by_xpath('.//a[@href="/jp/ShouhinSearch/"]').click()

    # 直接商品検索ページへいく
    page = 0

    saved_count: int = 0
    while True:
        page += 1
        driver.get(f'https://www.jins.com/jp/Search/All/1/?jcas=1#/Search/json?category=1&keyword=&page={page}&sort=3&angle=shomen')

        time.sleep(3)
        # 商品一覧を取得
        products_per_page: List[webdriver.remote.webelement.WebElement] = driver.find_element_by_id("asyncSearchResultView").find_elements_by_class_name('asyncProductWrapper')
        num_per_page = len(products_per_page)
        print('商品数' + str(num_per_page))
        if num_per_page < 1:
            break

        hrefs = []
        for product in products_per_page:
            link: WebElement = product.find_element_by_class_name("asyncProductImage").find_element_by_tag_name('a')
            hrefs.append(link.get_attribute("href"))


        current_num_in_current_page: int = 0
        while current_num_in_current_page < len(products_per_page):
            # products_per_page: List[webdriver.remote.webelement.WebElement] = driver.find_element_by_id("asyncSearchResultView").find_elements_by_class_name('asyncProductWrapper')
            # products_per_page[current].find_element_by_class_name("asyncProductImage").find_element_by_tag_name('a').click()
            driver.get(hrefs[current_num_in_current_page])
            time.sleep(3)

            # 商品名取得
            product_name = driver.find_element_by_id("goods_cd").text

            # バーチャルフィットチェックボタンクリック
            if is_virtualfit:
                vf_checkbox = driver.find_element_by_id("vtoCheck")
                if not vf_checkbox.is_selected():
                    driver.find_element_by_id("vtoCheckLabel").click()
                    time.sleep(5)

            color_list = driver.find_element_by_id("colorSelector").find_elements_by_tag_name("li")
            for i, c in enumerate(color_list):
                c.find_element_by_tag_name('a').find_element_by_tag_name('img').click()
                time.sleep(4)
                color_name = driver.find_element_by_id('dtlColor').text

                dir_name = "./downloads/"

                if is_virtualfit:
                    canvas: WebElement = driver.find_element_by_id("vto").find_element_by_tag_name('canvas')

                    offset_x = canvas.size['width'] / 12
                    for i in range(-6, 7, 1):
                        if i == 0:
                            webdriver.ActionChains(driver).context_click(canvas).perform()
                        else:
                            bias = - signed(i) * (offset_x / 2)
                            webdriver.ActionChains(driver).move_to_element(canvas).move_by_offset(offset_x * i + bias, 0).click().context_click().perform()

                        filename = dir_name + product_name + "_" + color_name + "_" + str(i+6) + ".png"

                        save_context_clicked_image(filename, is_virtualfit)
                        saved_count += 1

                else:
                    # img_src: str = driver.find_element_by_id("product_main_image_inner").find_element_by_tag_name("img").get_attribute('src')
                    img = driver.find_element_by_id("product_main_image_inner").find_element_by_tag_name("img")
                    webdriver.ActionChains(driver).context_click(img).perform()

                    filename = dir_name + product_name + "_" + color_name + "_glass" + ".png"

                    save_context_clicked_image(filename, is_virtualfit)
                    saved_count += 1

                print(filename)
                print(saved_count)
            current_num_in_current_page += 1
            driver.back()
# driver.close()


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
        canvas_base64 = driver.execute_script("return arguments[0].toDataURL('image/png').substring(21);", canvas)
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


def save_cookies(driver: ChromeDriver):
    pickle.dump(driver.get_cookies(), open(JINS_COOKIE_PATH, "wb"))


def load_cookies(driver: ChromeDriver):
    cookies = pickle.load(open(JINS_COOKIE_PATH, "rb"))
    for cookie in cookies:
        driver.add_cookie(cookie)


def check_exists_canvas(driver:ChromeDriver):
    try:
        driver.find_element_by_id("vto").find_element_by_tag_name('canvas')
    except NoSuchElementException:
        return False
    return True


def main():
    driver = create_driver()
    access(driver, is_virtualfit=True,  is_auth=False)


if __name__ == '__main__':
    main()

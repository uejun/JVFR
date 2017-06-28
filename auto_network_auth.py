# -*- coding: utf-8 -*-
import os
import time
from selenium import webdriver

# YNUネットワーク認証IDとPasswordを環境変数より取得
# ID = os.environ.get("YNU_AUTH_ID")
# PASS = os.environ.get("YNU_AUTH_PASS")
with open('.envrc', 'r') as f:
    lines = f.readlines()
    ID = lines[0].split('=')[1].replace('\n','').replace('\r','')
    PASS = lines[1].split('=')[1].replace('\n','').replace('\r','')

chrome_options = webdriver.ChromeOptions()
prefs = {"profile.default_content_setting_values.notifications" : 2}
chrome_options.add_experimental_option("prefs",prefs)
driver = webdriver.Chrome(chrome_options=chrome_options)
driver.implicitly_wait(10)
driver.set_page_load_timeout(30)

# YNUネットワーク認証
url = "http://1.1.1.1"
driver.get(url)
time.sleep(1)
driver.find_element_by_name("name").send_keys(ID)
time.sleep(1)
driver.find_element_by_name("pass").send_keys(PASS)
time.sleep(1)
driver.find_element_by_xpath('//input[@value="login"]').submit()
time.sleep(1)

driver.close()

import time
from selenium import webdriver


# driver = webdriver.Chrome()
chrome_options = webdriver.ChromeOptions()
prefs = {"profile.default_content_setting_values.notifications" : 2}
chrome_options.add_experimental_option("prefs",prefs)
driver = webdriver.Chrome(chrome_options=chrome_options)

driver.set_page_load_timeout(30)
url = "https://www.oruche.co.jp/"
driver.get(url)
driver.maximize_window()
driver.implicitly_wait(10)
driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
time.sleep(10)

driver.close()

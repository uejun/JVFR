import time
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import base64

# driver = webdriver.Chrome()
chrome_options = webdriver.ChromeOptions()
prefs = {"profile.default_content_setting_values.notifications" : 2}
chrome_options.add_experimental_option("prefs",prefs)
driver = webdriver.Chrome(chrome_options=chrome_options)

driver.set_page_load_timeout(30)
url = "https://www.w3schools.com/html/html5_canvas.asp"
driver.get(url)
driver.maximize_window()
canvas = driver.find_element_by_id("myCanvas3")
# canvas_base64 = driver.execute_script("return arguments[0].toDataURL('image/png').substring(21);", canvas)
#
# # decode
# canvas_png = base64.b64decode(canvas_base64)
#
# # save to a file
# filename = "canvas.png"
# with open(filename, 'wb') as f:
#     f.write(canvas_png)

actions = webdriver.ActionChains(driver)
actions.context_click(canvas)
actions.send_keys('V').send_keys(Keys.RETURN).send_keys(Keys.RETURN)
actions.perform()

import os
cmd = """
osascript -e 'tell application "System Events" to keystroke "v"'
"""
# minimize active window
os.system(cmd)

time.sleep(1)

cmd2 = """
osascript -e 'tell application "System Events" to key code 125'
"""
os.system(cmd2)

time.sleep(1)

# cmd3 = """
# osascript -e 'tell application "Chrome" to activate'
# """
# os.system(cmd3)

cmd4 = """
osascript -e 'tell application "System Events" to key code 36'
"""
os.system(cmd4)

time.sleep(3)
from PIL import ImageGrab, Image

im = ImageGrab.grabclipboard()
if isinstance(im, Image.Image):
    im.save('tmp.jpg')
    print('saved')
else:
    print('no image')

time.sleep(3)
# driver.close()
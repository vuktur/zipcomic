import os
from urllib.parse import urlparse
from urllib.request import urlopen, urlretrieve, Request
from zipfile import ZipFile
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.firefox import GeckoDriverManager
import imageio
from PIL import Image

driver = webdriver.Firefox(executable_path=GeckoDriverManager().install())
# driver.set_window_size(100, 100)


def netloc(): return urlparse(driver.current_url).netloc


def findBySel(selQ):
    url = driver.current_url
    if netloc() == "scansmangas.xyz":
        sels = {
            "chapsSel": "#chapter_list li .desktop>a",
            "titleSel": ".headpost h1",
            "pageSel": ".nav_apb a",
            "imgSel": ".area img"
        }
    if netloc() == "mangascan.cc":
        sels = {
            "chapsSel": ".chapters li a",
            "titleSel": ".page-header h1",
            "before-pageSel":".page-nav button.selectpicker.btn-primary",
            "pageSel": ".dropdown-menu.inner li>a",
            "imgSel": "#ppp img"
        }
    if netloc() == "mangascan.cc":
        sels = {
            "chapsSel": ".chapters li a",
            "titleSel": ".page-header h1",
            "before-pageSel":".page-nav button.selectpicker.btn-primary",
            "pageSel": ".dropdown-menu.inner li>a",
            "imgSel": "#ppp img"
        }
    res = driver.find_elements(By.CSS_SELECTOR, sels[selQ])
    if len(res) == 1: return res[0]
    else: return res


def getChaps(url):
    driver.get(url)
    l = [i.get_attribute("href") for i in findBySel("chapsSel")]
    return l[::-1]


def scrapChap(url):
    driver.get(url)
    title = findBySel("titleSel").get_attribute("innerText")
    print(title)
    path = f"C:/Users/vikto/Documents/{title}"
    try:
        os.mkdir(path)
    except FileExistsError:
        pass
    pgN = len(findBySel("pageSel"))
    if netloc() == "scansmangas.xyz":
            pgN = pgN-2
    for i in range(pgN):
        pagesElts = findBySel("pageSel")
        if netloc() == "scansmangas.xyz":
            pagesElts = pagesElts[1:-1]
        # if netloc() == "scansmangas.xyz":
        #     if n != 0: getImg(path, i, n)
        n = pagesElts[i]
        if n.get_attribute("href"):
            driver.get(n.get_attribute("href"))
        else:
            try: findBySel("before-pageSel").click()
            except: pass
            finally: n.click() 
        getImg(path, i, findBySel("imgSel").get_attribute("src"))
    # elif findBySel("nextSel"):
    #     nextBtn = findBySel("nextSel")


def getImg(path, i, src):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36'
    }
    req = Request(url=src, headers=headers)
    # urlretrieve(src,f"{path}/{n+1}.jpg")
    content = urlopen(req).read()
    img = imageio.imread(content)
    # try:
    # print(img)
    if len(img[0][0])>3:
        img2 = []
        for j in range(len(img)):
            img2.append([])
            for k in range(len(img[j])):
                img2[j].append(img[j][k][:-1])
        # img = [[img[i][j][:-1] for j in range(len(img[i]))]for i in range(len(img))]
        img = img2
    imageio.imwrite(f"{path.strip()}\\{i+1}.jpg", img)
    # except OSError:
    #     imageio.imwrite(f"{path.strip()}\\{i+1}.png", img)


print('============ START ============')
# chaps = getChaps("https://scansmangas.xyz/manga/gantz/")
# for i in chaps:
#     scrapChap(i)
# scrapChap(chaps[51])
chaps = getChaps("https://mangascan.cc/manga/vinland-saga")
scrapChap(chaps[94])
driver.quit()
print('============= END =============')

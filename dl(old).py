import os
from urllib.parse import urlparse
from urllib.request import urlopen, urlretrieve, Request
# from zipfile import ZipFile
from selenium import webdriver
# from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.firefox import GeckoDriverManager
import imageio
from PIL import Image


class Manga():

    def __init__(self, url, numList, localPath):
        self.baseUrl = url
        self.numList = numList
        self.localPath = localPath
        self.driver = webdriver.Firefox(
            executable_path=GeckoDriverManager().install())
        # self.driver.set_window_size(100, 100)
        self.go(url)
        for i in self.select("chaps")[::-1]:
            self.go(i.get_attribute("href"))
            self.scrapChapter()

    def __del__(self): self.driver.quit()

    def loc(self): return urlparse(self.driver.current_url).netloc

    def go(self,u): self.driver.get(u)

    def nextPage(self): pass
    
    def previousPage(self): pass

    def getPages(self): 
        pages = self.select("pages")
        if self.loc() == "scansmangas.xyz":
            return pages[1:-1]

    def select(self, q):
        selectors = {
            "chaps": {
                "scansmangas.xyz": "#chapter_list li .desktop>a",
                "mangascan.cc": ".chapters li a"
            },
            "title": {
                "scansmangas.xyz": ".headpost h1",
                "mangascan.cc": ".page-header h1"
            },
            "pages": {
                "scansmangas.xyz": ".nav_apb a",
                "mangascan.cc": ".dropdown-menu.inner li>a"
            },
            "image": {
                "scansmangas.xyz": ".area img",
                "mangascan.cc": "#ppp img"
            },
            "back": {
                "mangascan.cc": ".page-nav button.selectpicker.btn-primary"
            }
        }
        r = self.driver.find_elements(
            By.CSS_SELECTOR, selectors.get(q).get(self.loc()))
        return r[0] if len(r) == 1 else r

    def scrapChapter(self,n):
        title = self.select("title").get_attribute("innerText")
        path = self.localPath + title
        try:
            os.mkdir(path)
        except FileExistsError:
            pass
        pages = self.getPages()
        for i in range(len(self.getPages())):
            pages = self.getPages()
            # if netloc() == "scansmangas.xyz":
            #     if n != 0: getImg(path, i, n)
            p = pages[i]
            if p.get_attribute("href"):
                self.driver.get(p.get_attribute("href"))
            else:
                try:
                    self.select("back").click()
                except:
                    pass
                finally:
                    p.click()
            getImg(path, i, self.select("imgSel").get_attribute("src"))
        # elif findBySel("nextSel"):
        #     nextBtn = findBySel("nextSel")

    def getImg(path, i, src):
        userAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36"
        req = Request(url=src, headers={'User-Agent': userAgent})
        # urlretrieve(src,f"{path}/{n+1}.jpg")
        content = urlopen(req).read()
        img = imageio.imread(content)
        # try:
        # print(img)
        if len(img[0][0]) > 3:
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


if __name__ == "__main__":
    print('============ START ============')
    m = Manga("https://mangascan.cc/manga/vinland-saga", [94], os.getcwd())
    print('============= END =============')

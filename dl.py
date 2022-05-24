# from email import header
import os
import sys
# from wsgiref import headers
import requests as rqs
from bs4 import BeautifulSoup as bs
import fpdf
import html5lib
# from urllib.parse import urlparse
# from urllib.request import urlopen
# from zipfile import ZipFile
# from selenium import webdriver
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.webdriver.common.by import By
# from webdriver_manager.firefox import GeckoDriverManager
import imageio
from PIL import Image
import validators
import numpy as np


headers = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.136 Safari/537.36"
}


def progBar(i, tot, message="Loading"):
    y = int(i*100/tot)+1
    n = int(100-i*100/tot)-1
    print(f"{message} : \t[{'█'*y}{'_'*n}]", end='\r')
    if n <= 0:
        print(f"{message} - DONE{' '*105}", end='\n')


def main(source, url, sel, skipPages):
    if not validators.url(url):
        raise AttributeError
    r = rqs.get(url)
    S = getSiteSpecs(r.url)
    soup = bs(r.text, "html5lib")
    chaps = soup.select(S['chaptersListElt'])
    if S['chaptersListOrderDescending']:
        chaps = chaps[::-1]
    if type(sel) == int:
        if sel >= 0:
            scrapChap(chaps[sel].get('href'), skipPages)
        else:
            raise AttributeError
    elif (type(sel) == list or type(sel) == tuple) and len(sel) == 2 and type(sel[0]) == int:
        for i in range(sel[0], sel[1] if type(sel[1]) == int and sel[0] < sel[1] and sel[1] < len(chaps) else len(chaps)):
            scrapChap(chaps[i].get('href'), skipPages)
    else:
        raise AttributeError
    # driver = webdriver.Firefox(executable_path=GeckoDriverManager().install())
    # driver.set_window_size(100, 100)
    # driver.get(url)


def getSiteSpecs(url):
    domain = url.split('/')[2]
    specs = {
        # "scansmangas.xyz": {
        #     "chaptersListElt": "#chapter_list li .desktop>a",
        #     "title": ".headpost h1",
        #     "pageSel": ".nav_apb a",
        #     "pppImg": ".area img"
        # },
        "mangascan.cc": {
            "chaptersListElt": "ul.chapters li a",
            "chaptersListOrderDescending": True,
            "pageFormat": None,
            "title": ".page-header h1",
            "img": "#all img",
            "src": "data-src",
            "nextBtn": None
        },
        "mangakakalot.com": {
            "chaptersListElt": ".chapter-list .row a",
            "chaptersListOrderDescending": True,
            "pageFormat": None,
            "title": ".info-top-chapter h2",
            "img": ".container-chapter-reader img",
            "src": "src",
            "nextBtn": None
        },
        "oyasumipunpun.com": {
            "chaptersListElt": ".wp-block-gallery ul.su-posts li a",
            "chaptersListOrderDescending": True,
            "pageFormat": None,
            "title": "article header.entry-header h1",
            "img": ".entry-content .separator img",
            "src": "src",
            "nextBtn": None
        },
        "manga-scan.org": {
            "chaptersListElt": ".chapters-list a",
            "chaptersListOrderDescending": True,
            "pageFormat": "{url}/{n}",
            "title": "article header.entry-header h1",
            "img": ".entry-content .separator img",
            "src": "src",
            "nextBtn": ".btn-next"
        }
        # "japscan.ws": {                                            # CEST MORT YA UN SHADOWROOT
        #     "chaptersListElt": ".chapters_list .collapse a",
        #     "chaptersListOrderDescending":True,
        #     "inOnePage": True,
        #     "title": ".info-top-chapter h2",
        #     # "prev": ".previous a",
        #     # "next": ".next a",
        #     # "pageSel": ".dropdown-menu.inner li>a",
        #     # "pppImg": "#ppp img",
        #     "allImg": ".container-chapter-reader img",
        #     "src": "src"
        # }
    }
    if domain in specs:
        return specs[domain]


def scrapChap(url, skipPages):
    url = url.strip('/')
    r = rqs.get(url, headers=headers)
    S = getSiteSpecs(r.url)
    soup = bs(r.text, "html5lib")
    title = ''.join(list(map(lambda x: "_" if x in (" ", "/", "\\", ".")
                    else x, list(soup.select(S["title"])[0].text.strip()))))
    P = []
    H = 0
    W = 0
    n = 1
    btn = True
    while btn:
        r = rqs.get(S['pageFormat'].format(url=url, n=n)
                    if S['pageFormat'] else url, headers=headers)
        soup = bs(r.text, "html5lib")
        for i in soup.select(S['img']):
            P.append(i.get(S['src']))
            progBar(len(P), 1000, title)
        btn = soup.select(S['nextBtn']) if S['nextBtn'] else False
        n += 1
    for n, p in enumerate(P):
        if n+1 in skipPages:
            continue
        h, w, _ = openImage(p).shape
        if H < h:
            H = h
        if W < w:
            W = w
        progBar(n+1, 2*len(P), title)
    # if H < W:
    #     d = fpdf.FPDF('L', 'pt', (H, W))
    # else:
    d = fpdf.FPDF('P', 'pt', (W, H))
    for n, p in enumerate(P):
        if n+1 in skipPages:
            continue
        imageio.imwrite(f'temp{n}.jpg', openImage(p))
        d.add_page()
        # w = 210
        # h = 210*i.shape[1]/i.shape[0]
        d.image(f'temp{n}.jpg', 0, 0)  # , h, w)
        os.remove(f'temp{n}.jpg')
        progBar(len(P)+n+1, 2*len(P), title)
    d.output(f"{os.getcwd()}/{title}.pdf", dest='F')

    # if len(img[0][0]) > 3:
    #     img2 = []
    #     for j in range(len(img)):
    #         img2.append([])
    #         for k in range(len(img[j])):
    #             img2[j].append(img[j][k][:-1])
    # img = [[img[i][j][:-1] for j in range(len(img[i]))]for i in range(len(img))]
    # img = img2
    # NO ALPHA I GUESS?


def openImage(p):
    try:
        r = rqs.get(p, headers=headers)
        return imageio.imread(r.content)[:, :, :3]
    except:
        raise


if __name__ == "__main__":
    # main(*sys.argv)
    main("vscode", "https://mangascan.cc/manga/vinland-saga", sel=94, skipPages=[2])

# https://mangascan.cc/manga/vinland-saga
# https://www.japscan.ws/manga/bonne-nuit-punpun/
# https://mangakakalot.com/manga/sn926977

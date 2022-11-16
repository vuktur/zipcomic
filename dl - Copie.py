import io
import json
import os
import re
import warnings
from argparse import ArgumentParser
from collections import namedtuple
from datetime import datetime as dt
from urllib.parse import urlparse

import lxml
import numpy as np
import requests as rqs
from bs4 import BeautifulSoup as bs
from fpdf import FPDF
# import imageio.v3 as iio
from PIL import Image

HEADERS = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.136 Safari/537.36"
}

RMK_H = 1872
RMK_W = 1404


def progBar(i, tot, message="Loading"):
    y = i*100//tot
    n = 100-y
    print(f"{message} : \t[{'█'*y}{'_'*n}]", end='\r')
    if n <= 0:
        print(f"{message} - DONE{' '*105}", end='\n')


def parseNumList(sourceString):
    l = {}
    for num in sourceString.split(','):
        m = re.match(r'^(\d+)(?:-(\d+))?$', num)
        if not m:
            raise AttributeError(
                "The second parameter must be the selected chapters by numbers (ex: 1,3,6-9 will select chap. 1, 3 and the chaps. 6 to 9)")
        start = int(m.group(1))
        if m.group(2) and int(m.group(2)) >= int(m.group(1)):
            stop = int(m.group(2))
        else:
            stop = start
        for i in range(start, stop+1):
            l[i] = 1
    return sorted(l.keys())


def getSiteSpecs(url):
    netloc = urlparse(url).netloc
    allSpecs = json.load(open("./specs.json", 'r'))
    specsType = namedtuple('Specs', allSpecs["default"].keys())
    if netloc and netloc in allSpecs:
        return specsType._make(allSpecs[netloc].values())
    else:
        raise AttributeError("Bad url")


def scrap(url, pagesToSkip, dimMethod):
    S = getSiteSpecs(url)
    soup = bs(rqs.get(url, headers=HEADERS).text, "lxml")
    title = re.sub(r'[\s/\\.,]+', '_', soup.select(S.title)[0].text.strip())
    progBar(0, 1, title)
    pageList = []
    n = 1
    btn = True
    while btn:
        if S.pageFormat:
            soup = bs(rqs.get(S.pageFormat.format(url=url, n=n), headers=HEADERS).text, "lxml")
        for n, image in enumerate(soup.select(S.img)):
            if pagesToSkip and n+1 in pagesToSkip:
                continue
            pageList.append(image.get(S.src))
            # progBar(len(pageList), 1000, title)
        btn = soup.select(S.nextBtn) if S.nextBtn else False
        n += 1
    progBar(len(pageList), 2*len(pageList), title)
    # for i in range(len(pageList)):
    #     pageList[i] = openImage(pageList[i])
    #     progBar(len(pageList)+i+1, 3*len(pageList), title)
    # pageList = map(openImage, pageList) #cest ca qui prends du temps
    # pageList = [progBar(len(pageList)+n+1, 3*len(pageList), title) or openImage(p) for n, p in enumerate(pageList)]
    # pageShapes = np.array([p.shape[:2] for p in pageList])
    # if dimMethod == "max":
    #     pageWH = (max(pageShapes[:,1]), max(pageShapes[:,0]))
    # if dimMethod == "freq":
    #     pageWH = (np.median(pageShapes[:,1]), np.median(pageShapes[:,0]))
    # if dimMethod == "rmk":
    # pageWH = (RMK_W, RMK_H)
    pdfDoc = FPDF()
    for n, p in enumerate(pageList):
        # image = openImage(p)
        # iio.imwrite(f'temp{n}.jpg', image)
        # print(image.shape[0], image.shape[1])
        # if image.shape[1]<image.shape[0]:
        with Image.open(io.BytesIO(rqs.get(p).content)) as image:
            pdfDoc.add_page(format=(image.width, image.height))
        # else: 
            # pdfDoc.add_page('L', (image.shape[0], image.shape[1]))
        # w = h = 0
        # w = p.shape[1]
        # h = p.shape[0]
        # W = pageWH[0]
        # H = pageWH[1]
        # if w/h < W/H:
        #     w = w*H/h
        #     h = H
        # else:
        #     h = h*W/w
        #     w = W
        pdfDoc.image(image)
        # pdfDoc.image(f'temp{n}.jpg', 0, 0, 0, 0)
        # os.remove(f'temp{n}.jpg')
        progBar(len(pageList)+n+1, 2*len(pageList), title)
    pdfDoc.output(f"{os.getcwd()}/{title}.pdf")


# def openImage(pageUrl):
#     try:
#         image = iio.imread(rqs.get(pageUrl).content)
#         # print(type(image))
#         # print(image.shape)
#         # print(image[0])
#         # print('\n')
#         if len(image.shape) == 3:
#             return image[:, :, :3]
#         if len(image.shape) == 2:
#             return image#[[i,i,i] for j in image for i in image[j]]
#     except:
#         raise


def main(args):
    specs = getSiteSpecs(args.url)
    progBar(0, 1, "Getting chaps list")
    chaps = bs(rqs.get(args.url).text, "lxml").select(specs.chaptersListElt)
    progBar(1, 1, "Getting chaps list")
    if specs.chaptersListOrderDescending:
        chaps = chaps[::-1]
    for i in args.selectedChaps:
        if i >= len(chaps):
            warnings.warn(f"Chapter {i} and after are not available")
            break
        scrap(chaps[i].get('href'), args.pagesToSkip, args.dimMethod)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('url')
    parser.add_argument(
        '-s', '--select', dest='selectedChaps', type=parseNumList, default=0)
    parser.add_argument('-S', '--skip', dest='pagesToSkip',
                        type=parseNumList, default=None)
    parser.add_argument('-d', '--dim', dest='dimMethod',
                        choices=["freq", "max", "rmk"], default="freq")
    main(parser.parse_args())

# https://mangascan.cc/manga/vinland-saga
# https://www.japscan.ws/manga/bonne-nuit-punpun/
# https://mangakakalot.com/manga/sn926977


# py dl.py https://kaijimanga.com 0

# py dl.py https://kaijimanga.com -s 1,4-5,12-16

# todo chercher sur chaque site si il y a un resultat

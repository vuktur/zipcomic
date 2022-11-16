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


def handleError(err, url, args, action):
    retryMessage = f"An error has occured!\nurl : {url}\nerror : {str(err)}\nWould you like to continue? [y/n] "
    match action:
        case "skip":
            pass
        case "retry":
            scrap(url, args, "2ndtime")
        case "raise":
            raise
        case "2ndtime":
            print(
                "It's the 2nd time this error has occured, maybe there's a real problem!")
            raise
        case "ask":
            if input(retryMessage) == 'y':
                scrap(url, args, "ask")
            else:
                raise
        case _:
            if input(retryMessage) == 'y':
                scrap(url, args, "ask")
            else:
                raise


def scrap(chapUrl, args, onError=None):
    # if not onError:
    #     onError = args.onError
    S = getSiteSpecs(chapUrl)
    try:
        soup = bs(rqs.get(chapUrl, headers=HEADERS).text, "lxml")
    except rqs.exceptions.ConnectionError as err:
        handleError(err, chapUrl, args, onError or args.onError)
    title = re.sub(r'[\s/\\.,]+', '_', soup.select(S.title)[0].text.strip())
    progBar(0, 1, title)
    pageList = []
    n = 1
    while True:
        if S.pageFormat:
            soup = bs(rqs.get(S.pageFormat.format(
                url=chapUrl, n=n), headers=HEADERS).text, "lxml")
        for n, image in enumerate(soup.select(S.img)):
            if args.pagesToSkip and n+1 in args.pagesToSkip:
                continue
            pageList.append(image.get(S.src))
        if not S.nextBtn or not soup.select(S.nextBtn):
            break
        n += 1
    pdf = FPDF(unit="in")
    pdf.set_margins(0, 0)
    pdf.set_auto_page_break(False)
    for n, p in enumerate(pageList):
        with Image.open(io.BytesIO(rqs.get(p).content)) as image:
            pdf.add_page(format=(image.width/72, image.height/72))
            pdf.image(image)
        progBar(n+1, len(pageList), title)
    pdf.output(args.destPath+title+".pdf")


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
        scrap(chaps[i].get('href'), args)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('url')
    parser.add_argument(
        '-s', '--select', dest='selectedChaps', type=parseNumList, default=0)
    parser.add_argument('-S', '--skip', dest='pagesToSkip',
                        type=parseNumList, default=None)
    parser.add_argument('-d', '--dest', dest='destPath',
                        default=f"{os.getcwd()}/chaps/")
    parser.add_argument('-D', '--dim', dest='dimMethod',
                        choices=["freq", "max", "rmk"], default="freq")
    parser.add_argument('--onError', dest='onError',
                        choices=["skip", "retry", "raise", "ask"], default="ask")
    main(parser.parse_args())

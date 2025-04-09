import io
import json
import os
import re
import numpy as np
import warnings
from argparse import ArgumentParser
from collections import namedtuple
from urllib.parse import urlparse
from zipfile import ZipFile
from rarfile import RarFile

import requests as rqs
from bs4 import BeautifulSoup as bs, SoupStrainer
from fpdf import FPDF
from PIL import Image

USERAGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0 AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.136 Safari/537.36"
RMK_H = 1872
RMK_W = 1404


def progBar(i, tot, message="Loading"):
    if len(message) > 45: message = ''.join(message[0:42])+"..."
    y = i*100//tot
    n = 100-y
    print(f"{message} : \t[{'█'*y}{'_'*n}]", end='\r')
    if n <= 0:
        print(f"{message} : DONE{' '*105}", end='\n')


def parseSet(sourceString):
    s = set()
    for num in sourceString.split(','):
        m = re.match(r'^(\d+)(?:-(\d+))?$', num)
        if not m: raise AttributeError("The second parameter must be the selected chapters by numbers (ex: 1,3,6-9 will select chap. 1, 3 and the chaps. 6 to 9)")
        start = int(m.group(1))
        if m.group(2) and int(m.group(2)) >= int(m.group(1)):
            stop = int(m.group(2))
        else: stop = start
        s.update({i for i in range(start, stop+1)})
    return s


def getSiteSpecs(url):
    netloc = re.sub(r'^www\.', '', urlparse(url).netloc)
    allSpecs = json.load(open("./specs.json", 'r'))
    defaultSpecs = allSpecs["default"]
    SpecsType = namedtuple('Specs', tuple(defaultSpecs.keys()),
                           defaults=tuple(defaultSpecs.values()))
    if netloc and netloc in allSpecs:
        return SpecsType(**allSpecs[netloc])
    else: raise AttributeError(f"Bad url, netloc {netloc} not found in specs")


def strainSoup(sel):
    if not sel:
        return None
    m = re.match(r'^(#?)(\.?)(.*)', sel)
    return SoupStrainer(
            (m.group(3) if not m.group(1) and not m.group(2) else None),
            id=(m.group(3) if m.group(1) and not m.group(2) else None),
            class_=(m.group(3) if not m.group(1) and m.group(2) else None))


def handleError(err, url, args, action):
    if action == "ask":
        inp = input(f"An error has occured!\nurl : {url}\nerror : {str(err)}\nWhat would you like to do? [r(etry)/p(ass)/s(top)]")
        for act in ["retry", "pass", "stop"]:
            if act.startswith(inp): 
                handleError(err, url, args, act)
    if action == "retry":
        scrap(url, args, "2ndtime")
    if action == "pass":
        return 0
    if action == "stop":
        raise(err)
    if action == "2ndtime":
        print("It's the second time the following error occured, maybe there's a real problem!")
        handleError(err, url, args, "ask")


def decryptSquare(img):
    sqSize = 200
    squares = [img[i:sqSize+i, j:sqSize+j] for i in range(img.height/sqSize) for j in range(img.width/sqSize)]
    # squares = []


def translate(pages, title, dest):
    pass


def scrap(chapUrl, args, onError=None):
    specs = getSiteSpecs(chapUrl)
    headers = {"user-agent": USERAGENT, "referer": f"{urlparse(chapUrl).scheme}://{urlparse(chapUrl).netloc}/"}
    try:
        r = rqs.get(chapUrl, headers=headers)
    except rqs.exceptions.ConnectionError as err:
        handleError(err, chapUrl, args, onError or args.onError)
    titleSoup = bs(r.text, "lxml", parse_only=strainSoup(specs.title))
    title = re.sub(r'[<>:"/\\|?*\s\.,]+', '_', titleSoup.find().text.strip())
    title = '_'.join(f"{int(i):03}" if i.isdigit() else i for i in title.split('_'))
    progBar(0, 1, title)
    pages = []
    n = 1
    soup = bs(r.text, "lxml", parse_only=strainSoup(specs.imgList))
    while True:
        for i, image in enumerate(soup.select(specs.imgItem)):
            if i+1 in args.pagesToSkip: continue
            pages.append(image.get(specs.src))
        if specs.nextPage['btn'] and soup.select(specs.nextPage['btn']):
            try: r = rqs.get(specs.nextPage["urlFormat"].format(url=chapUrl, n=n), headers=headers)
            except rqs.exceptions.ConnectionError as err: handleError(err, chapUrl, args, onError or args.onError)
            soup = bs(r.text, "lxml")
            n += 1
        else: break
    # if args.doTranslate:
    #     translate(pages, title, args.destPath)
    progBar(0, 1, title)
    pdf = archive = None
    if args.destType == 'pdf':
        pdf = FPDF(unit="in")
        pdf.set_margins(0, 0)
        pdf.set_auto_page_break(False)
    if args.destType == 'zip':
        archive = ZipFile.open(args.destPath+title+".zip", 'w')
    if args.destType == 'rar':
        archive = RarFile.open(args.destPath+title+".rar", 'w')
    for n, p in enumerate(pages):
        try: imgBytes = io.BytesIO(rqs.get(p, headers=headers).content)
        except Image.UnidentifiedImageError: raise(f"Unable to access page {n} of chapter {title} at the url :\n{chapUrl}")
        img = None
        # if specs.imgEncrypt:
        #     img = decryptSquare(Image.open(imgBytes))
        if archive: 
            archive.writestr(f"{n:04}.png", imgBytes)
        if pdf: 
            img = img or Image.open(imgBytes)
            pdf.add_page(format=(img.width/72, img.height/72))
            pdf.image(img)
        if img: img.close()
        progBar(n+1, len(pages), title)
    if pdf: 
        pdf.output(args.destPath+title+".pdf")
    if archive: archive.close()


def main(args):
    specs = getSiteSpecs(args.url)
    progBar(0, 1, "Getting chaps list")
    parseOnly = strainSoup(specs.chapterList.format(cORv=args.byType, lang=args.lang))
    chaps = bs(rqs.get(args.url).text, "lxml")#, parse_only=parseOnly)
    print(chaps)
    chaps = chaps.select(specs.chapterItem)
    progBar(1, 1, "Getting chaps list")
    if specs.chapterListDescending:
        chaps = chaps[::-1]
    print(chaps)
    for i in args.selectedChaps:
        print(i)
        if i >= len(chaps):
            warnings.warn(f"Chapter {i} and after are not available")
            break
        parsedUrl = urlparse(args.url)
        href = re.sub(r'^\/', f"{parsedUrl.scheme}://{parsedUrl.netloc}/", chaps[i].get('href'))
        scrap(href, args)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('url')
    parser.add_argument('-s', '--select',    dest='selectedChaps', type=parseSet,                            default={0})
    parser.add_argument('-S', '--skip',      dest='pagesToSkip',   type=parseSet,                            default={})
    parser.add_argument('-d', '--dest',      dest='destPath',                                                default=f"{os.getcwd()}\\chaps\\")
    parser.add_argument('-E', '--onError',   dest='onError',       choices=["pass", "retry", "stop", "ask"], default="ask")
    parser.add_argument('-t', '--translate', dest='doTranslate',   action='store_true')
    parser.add_argument('-l', '--lang',      dest='lang',                                                    default='en')
    parser.add_argument(      '--by',        dest='byType',        choices=["chapter", "volume"],            default="chapter")
    fileTypeGroup = parser.add_mutually_exclusive_group()
    fileTypeGroup.add_argument('--pdf',      dest='destType',      action='store_const', const='pdf')
    fileTypeGroup.add_argument('--zip',      dest='destType',      action='store_const', const='zip')
    fileTypeGroup.add_argument('--rar',      dest='destType',      action='store_const', const='rar')
    # parser.add_argument('-D', '--dim',       dest='dimMethod',     choices=["freq", "max", "rmk"],           default="freq")
    parser.set_defaults(destType="pdf")
    main(parser.parse_args())

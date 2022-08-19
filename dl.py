import os
from re import A
import sys
import requests as rqs
from bs4 import BeautifulSoup as bs
import fpdf
import html5lib
import imageio
from PIL import Image
import validators
import numpy as np
import json


headers = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.136 Safari/537.36"
}


def progBar(i, tot, message="Loading"):
    y = int(i*100/tot)+1
    n = int(100-i*100/tot)-1
    print(f"{message} : \t[{'█'*y}{'_'*n}]", end='\r')
    if n <= 0:
        print(f"{message} - DONE{' '*105}", end='\n')


def getSiteSpecs(url):
    domain = url.split('/')[2]
    with open("./specs.json", 'r') as f:
        specs = json.load(f)
    if domain in specs:
        return specs[domain]


def scrapChap(url, pagesToSkip):
    url = url.strip('/')
    r = rqs.get(url, headers=headers)
    S = getSiteSpecs(r.url)
    soup = bs(r.text, "html5lib")
    title = ''.join(list(map(lambda x: "_" if x in (" ", "/", "\\", ".")
                    else x, list(soup.select(S["title"])[0].text.strip()))))
    P = []
    H = 0
    W = 0
    # FONCTIONNER PLUTOT PAR MOYENNE DE HAUTEUR ET LARGEUR ET LA MOYENNE SERA LA TRUC DE BASE ET POUR LES DOUBLES LES METTRE EN PETIT
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
        if n+1 in pagesToSkip:
            continue
        h, w, *_ = openImage(p).shape
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
        if n+1 in pagesToSkip:
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
        image = imageio.imread(r.content)
        if len(image.shape) == 3:
            return image[:, :, :3]
        else:
            return image
    except:
        print("/n", p)
        raise


def main(source, url, selectedChaps, skip=[]):
    if not validators.url(url):
        raise AttributeError
    r = rqs.get(url)
    S = getSiteSpecs(r.url)
    soup = bs(r.text, "html5lib")
    chaps = soup.select(S['chaptersListElt'])
    if S['chaptersListOrderDescending']:
        chaps = chaps[::-1]
    selectedChaps = selectedChaps.split(',')
    if skip != []:
        skip = skip.split(',')
    pagesToSkip = []
    for i in skip:
        try:
            i = list(map(int, i.split('-')))
            if i != sorted(i):
                raise AttributeError
            for j in range(i[0], i[1]+1 if len(i) == 2 else i[0]+1):
                pagesToSkip.append(j)
        except:
            raise
    for i in selectedChaps:
        try:
            i = list(map(int, i.split('-')))
            if i != sorted(i):
                raise AttributeError
            for j in range(i[0], (i[1]+1 if i[1] <= len(chaps) else len(chaps)+1) if len(i) == 2 else i[0]+1):
                scrapChap(chaps[j].get('href'), pagesToSkip)
        except:
            raise


if __name__ == "__main__":
    main(*sys.argv)

# https://mangascan.cc/manga/vinland-saga
# https://www.japscan.ws/manga/bonne-nuit-punpun/
# https://mangakakalot.com/manga/sn926977

// ==UserScript==
// @name     DL-manjikai
// @version  1
// @grant    none
// @match    https://one-piece-scan.com/manga/*
// @match    https://www.scan-fr.cc/manga/*
// @match    https://mangascan.cc/manga/*
// @match    https://7seeds-manga.com/manga/*
// @match    https://mangakakalot.tv/chapter/*
// @run-at   document-idle
// @require  https://raw.githubusercontent.com/Stuk/jszip/master/dist/jszip.min.js 
// @require  https://raw.githubusercontent.com/Stuk/jszip-utils/master/dist/jszip-utils.min.js
// @require  https://raw.githubusercontent.com/eligrey/FileSaver.js/master/dist/FileSaver.js
// ==/UserScript==

function getBinaryContent(path, callback) {
    function resolve(data) { callback(null, data) };
    function reject(err) { callback(err, null) };
    var xhr = new window.XMLHttpRequest();
    xhr.open('GET', path, true);
    xhr.responseType = "arraybuffer";
    // xhr.HEADERS_RECEIVED
    // xhr.setRequestHeader('Accept', 'image/webp, */*');
    // xhr.setRequestHeader('Accept-Encoding', 'gzip, deflate, br');
    // xhr.setRequestHeader('Accept-Language', 'fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3');
    // xhr.setRequestHeader('Cache-Control', 'max-age=0');
    // xhr.setRequestHeader('Connection', 'keep-alive');
    xhr.onreadystatechange = function (event) {
        if (this.readyState === 4) {
            if (this.status === 200 || this.status === 0) {
                try {
                    resolve(this.response || this.responseText);
                } catch (err) {
                    reject(new Error(err));
                }
            } else {
                reject(new Error("Ajax error for " + path + " : " + this.status + " " + this.statusText + "NIQUE TA GRZAND MERRRE LA PUTE FROBIDEN DE MERDE"));
            }
        }
    };
    xhr.send();
};

// function handleJPscan() {
//     for (let i = 0; i < 4; i++) {
//         document.querySelector('.reader-load-icon').style.display = "none";
//         if (window.getComputedStyle(document.querySelector('.show-long-strip')).getPropertyValue('display') === "none") {
//             document.querySelector('.reader-controls-mode-rendering').click();
//         };
//     };
//     let reader = document.querySelector('.reader-images');
//     let totalPages = parseInt(document.querySelector('.total-pages').innerHTML);
//     let i = 0;
//     let inter = setInterval( function() {
//         i++;
//         window.scrollTo(0, document.body.scrollHeight);
//         console.log(reader.childElementCount);
//         console.log(totalPages);
//         if (reader.childElementCount >= totalPages || i == 30) {
//             clearInterval(inter);
//             window.scrollTo(0, 0);
//         };
//     },100);
// }

async function initDL() {
    // let imglist = document.getElementsByTagName((website == 1 ? 'amp-img' : 'img'));
    let imglist = document.querySelectorAll(content + ' ' + (website == 1 ? 'amp-img' : 'img'));
    let zip = new JSZip();
    dlButton.setAttribute('disabled', true);
    dlButton.style.backgroundColor = "rgba(0,0,0,.7)";
    dlButton.style.pointerEvents = "none";
    updateLoadbar(0);
    changeStatus('gathering images');
    if (website === 3) {
        console.log(imglist);
    }
    await appendToZip(imglist, zip);
    changeStatus('preparing download');
    if (website == 1) {
        zip.remove('page -2.jpg');
        zip.remove('page -1.jpg');
    }
    downloadFile(zip);
    updateLoadbar(100);
    dlButton.removeAttribute('disabled');
    dlButton.style.backgroundColor = "rgba(0,0,0,0)";
    dlButton.style.pointerEvents = "auto";
}
async function appendToZip(imglist, zip) {
    let index, src, binary;
    let w = 0;
    for (let i = 0; i < imglist.length; i++) {
        switch (website) {
            case 1: {
                src = imglist[i].getAttribute('src');
                index = i - 2;
                break;
            }
            case 2: {
                if (imglist[i].getAttribute('data-src')) {
                    src = imglist[i].getAttribute('data-src');
                } else {
                    src = false;
                }
                index = i;
                break;
            }
            default: {
                src = imglist[i].getAttribute('src');
                index = i;
            }
        }
        if (src) {
            try {
                binary = await toBin(src);
                zip.file(`page ${index}.jpg`, binary, { binary: true });
                w = i / imglist.length * 100;
                changeStatus(`gathering images ${i}/${imglist.length}`);
                updateLoadbar(w);
            } catch (err) {
                changeStatus(err);
            }
        }
    }
}
function toBin(src) {
    return new Promise((resolve, reject) => {
        // JSZipUtils.getBinaryContent(src, (err, data) => {
        getBinaryContent(src, (err, data) => {
            if (err) {
                return reject(err);
            }
            return resolve(data);
        })
    })
}
function downloadFile(zip) {
    zip.generateAsync({ type: "blob" })
        .then(res => {
            changeStatus('click ok to download');
            let name = window.location.pathname.split('');
            switch (website) {
                case 1: name.splice(0, 12); name.splice(-8, 8); break;
                case 2: name.splice(0, 7); name.splice(-2, 2); break;
                case 3: name.splice(0, 7); break;
                case 4: name.splice(0, 7); name.splice(-1, 1); break;
                case 5: name.splice(0, 6); name.splice(-5, 5); break;
                default: name.splice(0, 1); break;
            }
            name = name.join('');
            name = name.replaceAll('-', '_');
            name = name.replaceAll('/', '_');
            saveAs(res, `${name}.zip`);
        }, errCode => changeStatus(errCode));
}
function updateLoadbar(w) {
    let p = document.querySelector('#dlman-progress');
    if (w < 100) {
        p.style.width = `${Math.round(w * 3)}px`;
    } else if (w == 100) {
        p.style.width = '300px';
        changeStatus('preparing download');
    }
}
function changeStatus(msg) {
    console.log(msg);
    dlParag.innerHTML = `status : ${msg}`;
}
let dlDiv = document.createElement('div');
dlDiv.id = 'dlman-div';
dlDiv.style = "position:absolute;top:100px;right:50px;z-index:100;background-color:navy;border-radius:15px;width:300px;box-sizing:border-box;display:flex;flex-direction:column";
let dlButton = document.createElement('button');
dlButton.id = 'dlman-btn';
dlButton.innerHTML = 'Download';
dlButton.style = "background-color:transparent;color:white;border-radius:15px 15px 0 0;margin:0;font-family:Helvetica,sans-serif;font-size:2em;font-weight:bold;border:none;padding:5px 0;text-align:center;user-select:none;cursor:pointer";
dlButton.addEventListener('click', initDL);
dlButton.addEventListener('mouseenter', function () { this.style.backgroundColor = 'rgba(0,0,0,.2)' });
dlButton.addEventListener('mouseleave', function () { this.style.backgroundColor = 'rgba(0,0,0,0)' });
dlButton.removeAttribute('disabled');
let dlLoadbar = document.createElement('div');
dlLoadbar.id = 'dlman-loadbar';
dlLoadbar.style = "background-color:#eee;height:5px";
let dlProgress = document.createElement('div');
dlProgress.id = 'dlman-progress';
dlProgress.style = "background-color:deepskyblue;height:5px;width:0px";
dlLoadbar.appendChild(dlProgress);
let dlParag = document.createElement('p');
dlParag.id = 'dlman-p';
dlParag.innerHTML = 'status : idle';
dlParag.style = "background-color:transparent;color:white;border-radius:15px 15px 0 0;font-family:Helvetica,sans-serif;font-size:1em;font-weight:normal;margin:10px";
dlDiv.appendChild(dlButton);
dlDiv.appendChild(dlLoadbar);
dlDiv.appendChild(dlParag);
let content, website;
switch (window.location.hostname) {
    case 'one-piece-scan.com': {
        content = 'article';
        website = 1;
        break;
    }
    case 'www.scan-fr.cc': {
        document.querySelector('#modeALL').click();
        content = '.viewer-cnt';
        website = 2;
        break;
    }
    case 'mangascan.cc': {
        document.querySelector('#modeALL').click();
        content = '.viewer-cnt';
        website = 2;
        break;
    }
    // case 'www.japanread.cc': {
    //     content = '#content';
    //     let inter = setInterval(function () {
    //         if (document.querySelector('img.noselect') !== null) {
    //             clearInterval(inter);
    //             console.log('ok');
    //             handleJPscan();
    //         }
    //     }, 10);
    //     website = 3;
    //     break;
    // }
    case '7seeds-manga.com': {
        content = '.entry-inner';
        website = 4;
        break;
    }
    case 'manhuascan.com': {
        content = '.chapter-content';
        website = 5;
        break;
    }
    default: alert('define main content area');
}
let firstChild = document.querySelector('body > *');
document.body.insertBefore(dlDiv, firstChild);
// document.styleSheets[0].insertRule('#dlman-div{position:absolute;top:100px;right:50px;background-color:navy;border-radius:15px;width:300px;box-sizing:border-box;display:flex;flex-direction:column}');
// document.styleSheets[0].insertRule('#dlman-btn{background-color:transparent;color:white;border-radius:15px 15px 0 0;font-family:Helvetica,sans-serif;font-size:2em;font-weight:bold;border:none;padding:5px 0;text-align:center;user-select:none;cursor:pointer}');
// document.styleSheets[0].insertRule('#dlman-btn:hover{background-color:#00000020}');
// document.styleSheets[0].insertRule('#dlman-btn:disabled{background-color:#00000070;cursor:default;pointer-events:none}');
// document.styleSheets[0].insertRule('#dlman-p{background-color:transparent;color:white;border-radius:15px 15px 0 0;font-family:Helvetica,sans-serif;font-size:1em;font-weight:normal;margin:10px}');
// document.styleSheets[0].insertRule('#dlman-loadbar{background-color:#eee;height:5px}');
// document.styleSheets[0].insertRule('#dlman-progress{background-color:deepskyblue;height:5px}');
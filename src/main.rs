mod fantoccini_tools;
mod progress;
mod selection;

use crate::fantoccini_tools::*;
use crate::progress::*;
use crate::selection::{Contains, Selection};
use clap::{Parser, ValueEnum};
use fantoccini::{error::CmdError, Client, ClientBuilder, Locator};
use once_cell::sync::Lazy;
use regex::Captures;
use regex::Regex;
use serde::{Deserialize, Serialize};
use serde_inline_default::serde_inline_default;
use serde_json::{self as json, json, Map, Value};
use std::io::BufReader;
use std::{fs, process::exit};
use tokio;
use tokio_stream::{self as stream, StreamExt};

const USER_AGENT: &str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0 AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.136 Safari/537.36";
// const RMK_H: usize = 1872;
// const RMK_W: usize = 1404;

#[derive(Parser, Debug)]
#[command(author, version, about)]
/// A simple manga scraper
struct Cli {
    /// URL to the page containing the list of chapters
    #[arg()]
    url: url::Url,

    /// Range of chapters to download
    #[arg(short = 's', long, value_name = "RANGE", value_parser = clap::value_parser!(Selection))]
    select: Selection,

    /// Range of pages to skip on every chapters
    #[arg(short = 'S', long, value_name = "RANGE", value_parser = clap::value_parser!(Selection))]
    skip: Option<Selection>,

    /// Destination path for the downloaded files
    #[arg(short = 'd', long, value_name = "PATH", value_parser = clap::value_parser!(std::path::PathBuf))]
    dest: Option<std::path::PathBuf>,

    /// Behaviour of the program when an error is encountered
    #[arg(short = 'E', long, value_enum)]
    onerr: Option<String>,

    /// Language to translate the pages to
    #[arg(short = 't', long, value_name = "LANG")]
    translate: Option<String>,

    /// Output type
    #[arg(value_enum, default_value_t = OutputType::Pdf)]
    otype: OutputType,
}

#[derive(Debug, Clone, ValueEnum)]
enum OutputType {
    /// Output as a pdf
    Pdf,
    /// Output as a zip
    Zip,
    /// Output as a rar
    Rar,
}

// enum ErrorBehaviour {}

#[serde_inline_default]
#[derive(Serialize, Deserialize)]
struct Parameters {
    /// The selector for the list of chapters
    #[serde_inline_default("body".to_string())]
    chapter_list: String,

    /// The selector for the link to a chapter in the list
    #[serde_inline_default("a".to_string())]
    chapter_item: String,

    /// Whether the chapter list is ordered form first to last or not
    #[serde_inline_default(true)]
    chapter_list_descending: bool,

    /// The selector for the title of the chapter
    #[serde_inline_default("h1".to_string())]
    title: String,

    /// The selector for the container of the images of the chapter
    #[serde_inline_default(None)]
    img_list: Option<String>,

    /// The selector for the images of the chapter
    #[serde_inline_default("img".to_string())]
    img_item: String,

    /// The name of the attribute containing the link to the image source
    #[serde_inline_default("src".to_string())]
    src: String,

    /// The information required to go from one page to the next
    #[serde_inline_default(NextPage::deserialize(Value::Object(Map::new())).unwrap())]
    next_page: NextPage,

    /// The encryption method used on the images
    #[serde_inline_default(None)]
    img_encrypt: Option<String>,
}

#[serde_inline_default]
#[derive(serde::Serialize, serde::Deserialize)]
struct NextPage {
    /// The selector for the button to click to go to the next page
    #[serde_inline_default(None)]
    btn: Option<String>,

    /// The format of the url of the next page
    #[serde_inline_default(None)]
    url_format: Option<String>,
}

fn get_parameters(host: &url::Host<&str>) -> json::Result<Parameters> {
    let path = format!("params\\{}.json", host);
    let res: Parameters = if let Some(file) = fs::File::open(path).ok() {
        let reader = BufReader::new(&file);
        json::from_value(json::from_reader::<BufReader<&fs::File>, Value>(reader)?)?
    } else {
        json::from_value(Value::Object(Map::new()))?
    };
    Ok(res)
}

async fn get_chapter_list(
    client: &Client,
    selection: &Selection,
    parameters: &Parameters,
    summary_url: &url::Url,
) -> Result<Vec<Option<String>>, CmdError> {
    // let s = s.replace("{cORv}", "chapter").replace("{lang}", "en");

    let list_selector = Locator::Css(String::as_str(&parameters.chapter_list));
    let chap_selector = Locator::Css(String::as_str(&parameters.chapter_item));

    client.goto(summary_url.as_str()).await?;

    let list = client.find(list_selector).await?;
    let chaps = list.find_all(chap_selector).await?;

    let chaps: &mut dyn Iterator<Item = _> = if parameters.chapter_list_descending {
        &mut chaps.iter().rev()
    } else {
        &mut chaps.iter()
    };

    let chaps = &mut chaps
        .enumerate()
        .filter(|(i, _)| selection.contains(i + 1))
        .map(|(_, a)| a);

    let base_url = &summary_url[..url::Position::BeforePath];

    let urls = stream::iter(chaps).then(|elt| async move {
        elt.prop("href").await.ok().flatten().map(|mut href| {
            if href.starts_with('/') {
                href.insert_str(0, base_url);
            }
            href
        })
    });

    tokio::pin!(urls);
    Ok(urls.collect().await)
}

async fn get_title(client: &Client, parameters: &Parameters) -> Result<String, CmdError> {
    static R_SPECIAL: Lazy<Regex> = Lazy::new(|| Regex::new(r#"[<>:"/\\|?*\s.,]+"#).unwrap());
    static R_NUMBER: Lazy<Regex> = Lazy::new(|| Regex::new(r#"[0-9]+"#).unwrap());

    let selector = Locator::Css(String::as_str(&parameters.title));

    let res = client.find(selector).await?.text().await?;

    let res = R_SPECIAL.replace_all(&res, "_");
    let res = R_NUMBER
        .replace(&res, |caps: &Captures| format!("{:0>3}", &caps[0]))
        .to_lowercase();

    Ok(res)
}

async fn get_images_same_page(
    client: &Client,
    parameters: &Parameters,
    skip_pages: &Option<Selection>,
    img_list_selector: &Option<Locator<'_>>,
    img_selector: &Locator<'_>,
) -> Result<Vec<Option<String>>, CmdError> {
    let images = find_all_in(client, img_list_selector, img_selector).await?;

    let images = images
        .iter()
        .enumerate()
        .filter(|(i, _)| !skip_pages.contains(i + 1))
        .map(|(_, a)| a);

    println!("{:?}", parameters.src);

    let res = stream::iter(images)
        .then(|img| async move { img.prop(&parameters.src).await.ok().flatten() });

    tokio::pin!(res);
    Ok(res.collect().await)
}

async fn get_images_multiple_pages(
    client: &Client,
    parameters: &Parameters,
    skip_pages: &Option<Selection>,
    img_list_selector: &Option<Locator<'_>>,
    img_selector: &Locator<'_>,
) -> Result<Vec<Option<String>>, CmdError> {
    let btn_selector = Locator::Css(parameters.next_page.btn.as_ref().unwrap());
    let mut res = Vec::<Option<String>>::new();
    let mut c: usize = 1;
    loop {
        if !skip_pages.contains(c) {
            let image_src = find_in(client, img_list_selector, img_selector)
                .await?
                .prop(&parameters.src)
                .await
                .ok()
                .flatten();

            res.push(image_src);
        }

        // nextpage.urlformat ???

        match client.find(btn_selector).await.ok() {
            Some(btn) => btn.click().await?,
            None => break,
        };
        c += 1;
    }
    Ok(res)
}

async fn get_chapter_images_urls(
    client: &Client,
    parameters: &Parameters,
    chapter_url: &str,
    skip_pages: &Option<Selection>,
) -> Result<Vec<Option<String>>, CmdError> {
    // ajouter onerror??
    // ajouter referer en header? proxy?

    let img_list_selector = &parameters
        .img_list
        .as_ref()
        .map(String::as_str)
        .map(Locator::Css);
    let img_selector = Locator::Css(&parameters.img_item);

    client.goto(chapter_url).await?;

    let title = get_title(&client, &parameters).await?;
    println!("{}", title);

    // progress_bar(0, 1, Some(&title));
    let pages: Vec<Option<String>> = if parameters.next_page.btn.is_some() {
        get_images_multiple_pages(
            client,
            parameters,
            skip_pages,
            &img_list_selector,
            &img_selector,
        )
        .await
    } else {
        get_images_same_page(
            client,
            parameters,
            skip_pages,
            &img_list_selector,
            &img_selector,
        )
        .await
    }?;

    // if parameters.translate.is_some() {}

    /*
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

    */
    Ok(pages)
}

#[tokio::main]
async fn main() -> Result<(), CmdError> {
    // let timer = time::Instant::now();

    for i in 0..101 {
        progress_bar(i, 0, Some("hey yo get off my cloud"));
        tokio::time::sleep(std::time::Duration::from_millis(10)).await;
    }
    // let cli = Cli::parse();
    let cli = Cli::parse_from(vec![
        "zipcomic",
        // "https://kaijimanga.com/",
        // "https://ww8.mangakakalot.tv/manga/manga-to955871",
        "https://sushiscan.net/catalogue/les-carnets-de-lapothicaire/",
        "-s 1-14"
        // "-s 1-4, 6, 27-29",
        // "-s 1-400",
    ]);

    let host = cli.url.host().unwrap();
    let parameters = get_parameters(&host).unwrap_or_else(|e| {
        eprintln!("error: Unable to retrieve parameters. {e}");
        exit(1);
    });

    // let client = reqwest::Client::builder()
    //     .user_agent(CUSTOM_USER_AGENT)
    //     .build()?;

    let caps = json!({
            "moz:firefoxOptions": {
                "args":["-headless"]
            }
        }).as_object().unwrap().clone();

    let client = ClientBuilder::native()
        .capabilities(caps)
        .connect("http://localhost:4444")
        .await
        .unwrap_or_else(|e| {
            eprintln!("error: Unable to connect to webdriver, please make sure that the driver is running. {e:?}");
            exit(1);
        });

    client.set_ua(USER_AGENT).await?;

    progress_bar(0, 1, Some("Fetching the chapters list"));

    let chapter_list = get_chapter_list(&client, &cli.select, &parameters, &cli.url).await;

    let chapter_list = chapter_list.unwrap_or_else(|e| match e {
        // CmdError::NoSuchElement(wd) => {
        //     panic!(
        //         "error: Chapter list element not found, check the json config and the url. {}",
        //         wd.message
        //     )
        // }
        CmdError::Standard(wd) => panic!("error: {}", wd.message),
        _ => panic!("error: Other error."),
    });

    progress_bar(1, 1, Some("Fetching the chapters list"));

    for href in chapter_list {
        if let Some(href) = href {
            println!("href : {:?}", href);
            let images_urls =
                get_chapter_images_urls(&client, &parameters, &href, &cli.skip).await?;
            println!("{:?}", images_urls);
            // download_chapter(&chap);
            println!();
        } else {
            println!("no href for a chapter.");
            println!();
        }
    }

    // println!("finish: {:?}", timer.elapsed());
    client.close().await
}

/*
def strainSoup(sel):
    if not sel:
        return None
    m = re.match(r'^(#?)(\.?)(.*)', sel)
    return SoupStrainer(
            (m.group(3) if not m.group(1) and not m.group(2) else None),
            id=(m.group(3) if m.group(1) and not m.group(2) else None),
            class_=(m.group(3) if not m.group(1) and m.group(2) else None))
*/

/*
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
*/

/*
def decryptSquare(img):
    sqSize = 200
    squares = [img[i:sqSize+i, j:sqSize+j] for i in range(img.height/sqSize) for j in range(img.width/sqSize)]
    # squares = []
*/

/*
def translate(pages, title, dest):
    pass
*/

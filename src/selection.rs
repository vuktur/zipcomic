use once_cell::sync::Lazy;
use regex::Regex;
use std::{ops::Range, str::FromStr};

// #[derive(Debug, Clone)]
// pub enum ParsedRangeElt {
//     Single(usize),
//     Range(usize, usize),
// }

pub trait Contains {
    fn contains(&self, i: usize) -> bool;
}

#[allow(dead_code)]
#[derive(Debug, Clone)]
pub struct Selection(Vec<Range<usize>>);

impl FromStr for Selection {
    type Err = String;

    /// The input for this function should be something like this : `2-6, 9, 12-16`
    fn from_str(s: &str) -> Result<Selection, Self::Err> {
        let error_msg = String::from("error: The value must follow the format 2-6, 9, 12-16.");
        static RSEP: Lazy<Regex> = Lazy::new(|| Regex::new(r#"[ ,]+"#).unwrap());
        static RRANGE: Lazy<Regex> = Lazy::new(|| Regex::new(r#"^(\d+)(?:-(\d+))?$"#).unwrap());
        let mut res: Vec<Range<usize>> = Vec::new();
        for range_str in RSEP.split(s) {
            if range_str.len() == 0 {
                continue;
            }
            let caps: Vec<Option<usize>> = RRANGE
                .captures(range_str)
                .expect(&error_msg)
                .iter()
                .skip(1)
                .take(2)
                .map(|opt| opt.map(|m| m.as_str().parse::<usize>().ok()).flatten())
                .collect();
            let range = match caps[..] {
                [Some(l), Some(u)] => l..u + 1,
                [Some(l), None] => l..l + 1,
                _ => Err(&error_msg)?,
            };
            res.push(range);
        }
        Ok(Selection(res))
    }
}

impl Contains for Selection {
    fn contains(&self, i: usize) -> bool {
        self.0.iter().any(|range| range.contains(&i))
    }
}

impl Contains for Option<Selection> {
    fn contains(&self, i: usize) -> bool {
        self.as_ref().map_or(false, |sel| sel.contains(i))
    }
}

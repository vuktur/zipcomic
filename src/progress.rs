use std::io::Write;

const WIDTH: usize = 30;

#[allow(dead_code)]
pub fn progress_bar(progress: usize, total: usize, message: Option<&str>) {
    let p = progress * WIDTH / (if total == 0 { 100 } else { total });
    let message = message.map_or("Loading...", |m| if m.len() > 45 { &m[..42] } else { m });
    let progress: String = if p < WIDTH {
        format!("[{}]", (0..WIDTH).map(|i| if i < p { '█' } else { '░' }).collect::<String>())
    } else {
        format!("complete{}\n", " ".repeat(WIDTH - 6))
    };
    print!("{} : \t{}\r", message, progress);
    std::io::stdout().flush().unwrap();
}
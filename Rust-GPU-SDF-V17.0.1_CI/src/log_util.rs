// V15.9.9.1: DCシェーダーコンパイル診断用の永続ログ基盤
use std::io::Write;
use std::path::{Path, PathBuf};
use std::sync::OnceLock;

static LOG_PATH: OnceLock<PathBuf> = OnceLock::new();

const MAX_LOG_BYTES: u64 = 2 * 1024 * 1024; // 2MB

/// Python から渡される cache_path (shader_cache.bin) の親ディレクトリを流用し、
/// 同じフォルダに sdf_debug.log を配置する。init_gpu の冒頭で一度だけ呼ばれる想定。
pub fn init_log_path(dir: &Path) {
    let path = dir.join("sdf_debug.log");

    // 肥大化防止の簡易ローテーション: 既存ファイルが上限を超えていたら .old にリネーム
    if let Ok(meta) = std::fs::metadata(&path) {
        if meta.len() > MAX_LOG_BYTES {
            let old_path = dir.join("sdf_debug.log.old");
            let _ = std::fs::rename(&path, &old_path);
        }
    }

    let _ = LOG_PATH.set(path);
}

fn timestamp() -> String {
    match std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH) {
        Ok(d) => format!("{}.{:03}", d.as_secs(), d.subsec_millis()),
        Err(_) => "0.000".to_string(),
    }
}

/// ファイルへ追記 + 既存どおり stdout にも出力する。ログパス未設定の場合は stdout のみ。
pub fn log_line(msg: &str) {
    if let Some(path) = LOG_PATH.get() {
        if let Ok(mut f) = std::fs::OpenOptions::new().create(true).append(true).open(path) {
            let _ = writeln!(f, "[{}] {}", timestamp(), msg);
        }
    }
    println!("{}", msg);
}

/// 現在有効なログファイルの絶対パスを返す (Python 側での案内表示用)
pub fn get_log_path() -> Option<String> {
    LOG_PATH.get().map(|p| p.to_string_lossy().into_owned())
}

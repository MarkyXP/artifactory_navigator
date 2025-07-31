use std::fs::{self, File};
use std::io::{self, Read};
use std::path::Path;
use serde_json;
use serde::{Deserialize, Serialize};
use expand_str;
use std::process::Command;

#[derive(Debug, Serialize, Deserialize)]
struct Config {
    exe_filename : String,
    launch_flags : String,
    master_path_version_str: String,
    local_path_version_str: String,
}

fn expand_env_vars(path: &str) -> String {
    let expanded = expand_str::expand_string_with_env(path).unwrap();//.into_owned();
    println!("{}", expanded);
    expanded
}

fn main() -> io::Result<()> {
    // Read the config file
    let mut config_file: File = File::open("updater_config.json")?;
    let mut config_content: String = String::new();
    config_file.read_to_string(&mut config_content)?;
    let config: Config = serde_json::from_str(&config_content)?;
    // Get the master data location
    let raw_master_data_loc = config.master_path_version_str;
    let expanded_master_data_loc = expand_env_vars(&raw_master_data_loc);
    let master_version_path = Path::new(&expanded_master_data_loc);
    let master_path = master_version_path.parent().unwrap();
    // Get the appdata location
    let raw_appdata_loc = config.local_path_version_str;
    let expanded_appdata_loc = expand_env_vars(&raw_appdata_loc);
    let appdata_version_path = Path::new(&expanded_appdata_loc);
    let appdata_path = appdata_version_path.parent().unwrap();
    let appdata_path_str = appdata_path.to_string_lossy().into_owned();
    let appdata_exe = format!("{}\\{}", appdata_path_str, &config.exe_filename);

    // Check if the bedrock version file exists
    if master_version_path.exists() {
        println!("Master version file found.");
    } else {
        println!("Master version file not found. Launching from APPDATA...");
        launch_app_with_updater_flag(&appdata_exe, &config.launch_flags)?;
        return Ok(())
    }

    // Check if the appdata version file exists and compare MD5
    if !Path::new(&appdata_version_path).exists() {
        println!("APPDATA version file not found. Copying from bedrock...");
        copy_files_from_master_to_appdata(&master_path, &appdata_path)?;
    } else {
        let bedrock_ver = read(&master_version_path)?;
        let appdata_ver = read(&appdata_version_path)?;

        if bedrock_ver != appdata_ver {
            println!("MD5 mismatch. Copying from bedrock...");
            copy_files_from_master_to_appdata(&master_path, &appdata_path)?;
        } else {
            println!("MD5 match. No need to copy.");
        }
    }

    // Launch the application with the updater flag
    println!("Launching app!");
    launch_app_with_updater_flag(&appdata_exe, &config.launch_flags)?;

    Ok(())
}

fn read(file_path: &Path) -> io::Result<String> {
    let mut src_file: File = File::open(file_path)?;
    let mut src_content: String = String::new();
    src_file.read_to_string(&mut src_content)?;
    Ok(src_content.to_string())
}

fn copy_files_from_master_to_appdata(master_path: &Path, appdata_path: &Path) -> io::Result<()> {
    if !Path::new(appdata_path).exists() {
        fs::create_dir_all(appdata_path)?;
    }
    let src_path_str = appdata_path.to_str().unwrap();
    for entry in master_path.read_dir()? {
        let entry = entry?;
        let path = entry.path();
        if path.is_dir() {
            continue;
        }
        let src_file_name = path.file_name().unwrap().to_str().unwrap();
        let target_path_str = format!("{}/{}", src_path_str, src_file_name);
        let target_path = Path::new(&target_path_str);
        fs::copy(&path, &target_path)?;
    }
    Ok(())
}

fn launch_app_with_updater_flag(exe_path: &String, flag : &String) -> io::Result<()> {
    Command::new(exe_path)
        .arg(flag)
        .arg("TRUE")
        .spawn()?;
    Ok(())
}
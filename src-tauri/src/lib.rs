use std::env;
use std::process::Child;
use std::process::Command;
use std::process::Stdio;
use std::sync::Mutex;

use tauri::AppHandle;
use tauri::Manager;
use tauri::RunEvent;

struct ApiSidecarState(Mutex<Option<Child>>);

impl Default for ApiSidecarState {
  fn default() -> Self {
    Self(Mutex::new(None))
  }
}

fn should_skip_sidecar() -> bool {
  matches!(env::var("APKHACKER_SKIP_SIDECAR").ok().as_deref(), Some("1"))
}

fn sidecar_command() -> String {
  env::var("APKHACKER_API_COMMAND")
    .unwrap_or_else(|_| "python3 -m apk_hacker.interfaces.api_fastapi.main".to_string())
}

#[cfg(target_os = "macos")]
fn maybe_spawn_api_sidecar(app_handle: &AppHandle) {
  if should_skip_sidecar() {
    return;
  }

  let state = app_handle.state::<ApiSidecarState>();
  let Ok(mut guard) = state.0.lock() else {
    return;
  };
  if guard.is_some() {
    return;
  }

  let command = sidecar_command();
  match Command::new("/bin/sh")
    .arg("-lc")
    .arg(&command)
    .stdout(Stdio::null())
    .stderr(Stdio::inherit())
    .spawn()
  {
    Ok(child) => {
      *guard = Some(child);
    }
    Err(error) => {
      eprintln!("failed to start APKHacker API sidecar `{command}`: {error}");
    }
  }
}

#[cfg(not(target_os = "macos"))]
fn maybe_spawn_api_sidecar(_app_handle: &AppHandle) {}

fn shutdown_api_sidecar(app_handle: &AppHandle) {
  let state = app_handle.state::<ApiSidecarState>();
  let Ok(mut guard) = state.0.lock() else {
    return;
  };
  let Some(mut child) = guard.take() else {
    return;
  };

  if let Err(error) = child.kill() {
    eprintln!("failed to stop APKHacker API sidecar: {error}");
  }
  let _ = child.wait();
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  let app = tauri::Builder::default()
    .plugin(tauri_plugin_dialog::init())
    .plugin(tauri_plugin_shell::init())
    .manage(ApiSidecarState::default())
    .setup(|app| {
      maybe_spawn_api_sidecar(app.handle());
      Ok(())
    })
    .build(tauri::generate_context!())
    .expect("error while building tauri application");

  app.run(|app_handle, event| {
    if matches!(event, RunEvent::ExitRequested { .. } | RunEvent::Exit) {
      shutdown_api_sidecar(app_handle);
    }
  });
}

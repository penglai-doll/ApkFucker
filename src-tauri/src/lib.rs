use std::env;
use std::fs;
use std::path::Path;
use std::path::PathBuf;
use std::process::Child;
use std::process::Command;
use std::process::Stdio;
use std::sync::Mutex;

use tauri::AppHandle;
use tauri::Manager;
use tauri::RunEvent;

struct ApiSidecarState(Mutex<Option<Child>>);

const DEFAULT_API_HOST: &str = "127.0.0.1";
const DEFAULT_API_PORT: &str = "8765";
const DEFAULT_API_BASE_URL: &str = "http://127.0.0.1:8765";

impl Default for ApiSidecarState {
  fn default() -> Self {
    Self(Mutex::new(None))
  }
}

fn should_skip_sidecar() -> bool {
  matches!(env::var("APKHACKER_SKIP_SIDECAR").ok().as_deref(), Some("1"))
}

fn repo_root() -> PathBuf {
  PathBuf::from(env!("CARGO_MANIFEST_DIR"))
    .parent()
    .map(Path::to_path_buf)
    .unwrap_or_else(|| PathBuf::from(env!("CARGO_MANIFEST_DIR")))
}

#[derive(Debug)]
struct SidecarLaunchSpec {
  program: PathBuf,
  args: Vec<String>,
  cwd: Option<PathBuf>,
  envs: Vec<(String, String)>,
}

fn default_sidecar_envs() -> Vec<(String, String)> {
  vec![
    ("APKHACKER_API_HOST".to_string(), DEFAULT_API_HOST.to_string()),
    ("APKHACKER_API_PORT".to_string(), DEFAULT_API_PORT.to_string()),
    ("APKHACKER_API_BASE_URL".to_string(), DEFAULT_API_BASE_URL.to_string()),
    ("PYTHONUNBUFFERED".to_string(), "1".to_string()),
  ]
}

fn sidecar_shell_command(command: String) -> SidecarLaunchSpec {
  let (program, args) = if cfg!(target_os = "windows") {
    (PathBuf::from("cmd"), vec!["/C".to_string(), command])
  } else {
    (PathBuf::from("/bin/sh"), vec!["-lc".to_string(), command])
  };
  SidecarLaunchSpec {
    program,
    args,
    cwd: None,
    envs: default_sidecar_envs(),
  }
}

fn command_candidates(name: &str) -> Vec<String> {
  if !cfg!(target_os = "windows") || Path::new(name).extension().is_some() {
    return vec![name.to_string()];
  }

  let mut candidates = vec![name.to_string()];
  let pathext = env::var("PATHEXT").unwrap_or_else(|_| ".EXE;.CMD;.BAT;.COM".to_string());
  for extension in pathext.split(';') {
    let normalized = extension.trim();
    if normalized.is_empty() {
      continue;
    }
    candidates.push(format!("{name}{normalized}"));
    candidates.push(format!("{name}{}", normalized.to_ascii_lowercase()));
  }
  candidates
}

fn command_in_path(name: &str) -> Option<PathBuf> {
  let paths = env::var_os("PATH")?;
  env::split_paths(&paths)
    .flat_map(|entry| {
      command_candidates(name)
        .into_iter()
        .map(move |candidate| entry.join(Path::new(&candidate)))
    })
    .find(|candidate| candidate.is_file())
}

fn looks_like_project_root(path: &Path) -> bool {
  path.join("pyproject.toml").is_file() && path.join("src").join("apk_hacker").is_dir()
}

fn find_project_root(start: &Path) -> Option<PathBuf> {
  start
    .ancestors()
    .find(|candidate| looks_like_project_root(candidate))
    .map(Path::to_path_buf)
}

fn packaged_resource_root() -> Option<PathBuf> {
  #[cfg(target_os = "macos")]
  {
    let current_exe = env::current_exe().ok()?;
    let exe_dir = current_exe.parent()?;
    let contents_dir = exe_dir.parent()?;
    let resources_dir = contents_dir.join("Resources");
    if resources_dir.is_dir() {
      return Some(resources_dir);
    }

    None
  }

  #[cfg(not(target_os = "macos"))]
  {
    None
  }
}

fn packaged_project_root() -> Option<PathBuf> {
  let resources_dir = packaged_resource_root()?;
  if looks_like_project_root(&resources_dir) {
    return Some(resources_dir);
  }

  None
}

fn inferred_project_root_from_current_exe() -> Option<PathBuf> {
  let current_exe = env::current_exe().ok()?;
  let start = current_exe.parent()?;
  find_project_root(start)
}

fn python_path_for(project_root: &Path) -> Option<String> {
  let source_root = project_root.join("src");
  if source_root.is_dir() {
    return Some(source_root.to_string_lossy().into_owned());
  }

  None
}

fn app_sidecar_env_root(app_handle: &AppHandle) -> Option<PathBuf> {
  let app_data_dir = app_handle.path().app_data_dir().ok()?;
  let sidecar_root = app_data_dir.join("sidecar");
  if fs::create_dir_all(&sidecar_root).is_ok() {
    return Some(sidecar_root);
  }

  None
}

fn uv_sidecar_spec(project_root: PathBuf, app_handle: &AppHandle) -> Option<SidecarLaunchSpec> {
  let uv = command_in_path("uv")?;
  let mut envs = default_sidecar_envs();
  if let Some(sidecar_root) = app_sidecar_env_root(app_handle) {
    envs.push((
      "UV_PROJECT_ENVIRONMENT".to_string(),
      sidecar_root.join(".venv").to_string_lossy().into_owned(),
    ));
    envs.push((
      "UV_CACHE_DIR".to_string(),
      sidecar_root.join("uv-cache").to_string_lossy().into_owned(),
    ));
  }
  Some(SidecarLaunchSpec {
    program: uv,
    args: vec![
      "run".to_string(),
      "python".to_string(),
      "-m".to_string(),
      "uvicorn".to_string(),
      "apk_hacker.interfaces.api_fastapi.main:app".to_string(),
      "--host".to_string(),
      DEFAULT_API_HOST.to_string(),
      "--port".to_string(),
      DEFAULT_API_PORT.to_string(),
    ],
    cwd: Some(project_root),
    envs,
  })
}

fn python_sidecar_spec(project_root: PathBuf) -> Option<SidecarLaunchSpec> {
  let python = command_in_path("python3").or_else(|| command_in_path("python"))?;
  let mut envs = default_sidecar_envs();
  if let Some(python_path) = python_path_for(&project_root) {
    envs.push(("PYTHONPATH".to_string(), python_path));
  }
  Some(SidecarLaunchSpec {
    program: python,
    args: vec![
      "-m".to_string(),
      "uvicorn".to_string(),
      "apk_hacker.interfaces.api_fastapi.main:app".to_string(),
      "--host".to_string(),
      DEFAULT_API_HOST.to_string(),
      "--port".to_string(),
      DEFAULT_API_PORT.to_string(),
    ],
    cwd: Some(project_root),
    envs,
  })
}

fn path_sidecar_spec() -> Option<SidecarLaunchSpec> {
  let binary = command_in_path("apk-hacker-api")?;
  Some(SidecarLaunchSpec {
    program: binary,
    args: Vec::new(),
    cwd: None,
    envs: default_sidecar_envs(),
  })
}

fn sidecar_spec(app_handle: &AppHandle) -> SidecarLaunchSpec {
  if let Ok(command) = env::var("APKHACKER_API_COMMAND") {
    return sidecar_shell_command(command);
  }

  if cfg!(debug_assertions) {
    let root = repo_root();
    if let Some(spec) = uv_sidecar_spec(root.clone(), app_handle) {
      return spec;
    }
    if let Some(spec) = python_sidecar_spec(root) {
      return spec;
    }
  }

  if let Some(root) = packaged_project_root() {
    if let Some(spec) = uv_sidecar_spec(root.clone(), app_handle) {
      return spec;
    }
    if let Some(spec) = python_sidecar_spec(root) {
      return spec;
    }
  }

  if let Some(root) = inferred_project_root_from_current_exe() {
    if let Some(spec) = uv_sidecar_spec(root.clone(), app_handle) {
      return spec;
    }
    if let Some(spec) = python_sidecar_spec(root) {
      return spec;
    }
  }

  if let Some(spec) = path_sidecar_spec() {
    return spec;
  }

  sidecar_shell_command("apk-hacker-api".to_string())
}

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

  let spec = sidecar_spec(app_handle);
  let display_command = if spec.args.is_empty() {
    spec.program.to_string_lossy().into_owned()
  } else {
    format!(
      "{} {}",
      spec.program.to_string_lossy(),
      spec.args.join(" ")
    )
  };
  let mut command = Command::new(&spec.program);
  command
    .args(&spec.args)
    .stdout(Stdio::null())
    .stderr(Stdio::inherit());
  if let Some(cwd) = &spec.cwd {
    command.current_dir(cwd);
  }
  command.envs(spec.envs.iter().map(|(key, value)| (key, value)));
  match command.spawn() {
    Ok(child) => {
      *guard = Some(child);
    }
    Err(error) => {
      eprintln!("failed to start APKHacker API sidecar `{display_command}`: {error}");
    }
  }
}

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

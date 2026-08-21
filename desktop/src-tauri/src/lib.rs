#![deny(unsafe_code)]

use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::io::{BufReader, Read, Write};
use std::path::{Path, PathBuf};
use std::process::{Child, ChildStdin, ChildStdout, Command, Stdio};
use std::sync::Mutex;
use tauri::{WebviewUrl, WebviewWindow, WebviewWindowBuilder};
use uuid::Uuid;

const PROTOCOL_VERSION: &str = "1.0";
const MAX_FRAME_BYTES: usize = 65_536;
const MAX_TEXT: usize = 512;
const ALLOWED_ORIGINS: &[(&str, &str)] = &[("tauri", "localhost"), ("http", "tauri.localhost")];

#[derive(Debug, Serialize)]
struct SidecarRequest<'a> {
    version: &'static str,
    command: &'static str,
    correlation_id: String,
    session_token: Option<&'a str>,
    payload: Value,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct SidecarResponse {
    version: String,
    correlation_id: String,
    status: String,
    #[serde(default)]
    data: Option<Value>,
    #[serde(default)]
    error: Option<SidecarError>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct SidecarError {
    code: String,
}

struct SidecarClient {
    _child: Child,
    stdin: ChildStdin,
    stdout: BufReader<ChildStdout>,
}

impl SidecarClient {
    fn spawn() -> Result<Self, String> {
        let path = locate_sidecar().ok_or_else(|| "SIDECAR_UNAVAILABLE".to_string())?;
        let temp_directory = std::env::temp_dir();
        let mut child = Command::new(path)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::null())
            .env_clear()
            .env(
                "SYSTEMROOT",
                std::env::var("SYSTEMROOT").unwrap_or_default(),
            )
            .env("WINDIR", std::env::var("WINDIR").unwrap_or_default())
            // The single-file Python sidecar must unpack before it can start.
            // These host-owned values are fixed by the Rust boundary and are
            // never accepted from renderer request data.
            .env("TEMP", &temp_directory)
            .env("TMP", &temp_directory)
            .spawn()
            .map_err(|_| "SIDECAR_UNAVAILABLE".to_string())?;
        let stdin = child
            .stdin
            .take()
            .ok_or_else(|| "SIDECAR_UNAVAILABLE".to_string())?;
        let stdout = child
            .stdout
            .take()
            .ok_or_else(|| "SIDECAR_UNAVAILABLE".to_string())?;
        Ok(Self {
            _child: child,
            stdin,
            stdout: BufReader::new(stdout),
        })
    }

    fn invoke(
        &mut self,
        command: &'static str,
        session_token: Option<&str>,
        payload: Value,
    ) -> Result<Value, String> {
        let correlation_id = Uuid::new_v4().simple().to_string();
        let request = SidecarRequest {
            version: PROTOCOL_VERSION,
            command,
            correlation_id: correlation_id.clone(),
            session_token,
            payload,
        };
        let body = serde_json::to_vec(&request).map_err(|_| "REQUEST_INVALID".to_string())?;
        if body.is_empty() || body.len() > MAX_FRAME_BYTES {
            return Err("REQUEST_INVALID".to_string());
        }
        self.stdin
            .write_all(&(body.len() as u32).to_be_bytes())
            .and_then(|_| self.stdin.write_all(&body))
            .and_then(|_| self.stdin.flush())
            .map_err(|_| "SIDECAR_IO_FAILED".to_string())?;

        let mut header = [0_u8; 4];
        self.stdout
            .read_exact(&mut header)
            .map_err(|_| "SIDECAR_IO_FAILED".to_string())?;
        let length = u32::from_be_bytes(header) as usize;
        if length == 0 || length > MAX_FRAME_BYTES {
            return Err("SIDECAR_PROTOCOL_FAILED".to_string());
        }
        let mut response_body = vec![0_u8; length];
        self.stdout
            .read_exact(&mut response_body)
            .map_err(|_| "SIDECAR_IO_FAILED".to_string())?;
        let response: SidecarResponse = serde_json::from_slice(&response_body)
            .map_err(|_| "SIDECAR_PROTOCOL_FAILED".to_string())?;
        if response.version != PROTOCOL_VERSION || response.correlation_id != correlation_id {
            return Err("SIDECAR_PROTOCOL_FAILED".to_string());
        }
        match response.status.as_str() {
            "ok" => response
                .data
                .ok_or_else(|| "SIDECAR_PROTOCOL_FAILED".to_string()),
            "error" => Err(response
                .error
                .map(|error| sanitize_code(&error.code))
                .unwrap_or_else(|| "OPERATION_FAILED".to_string())),
            _ => Err("SIDECAR_PROTOCOL_FAILED".to_string()),
        }
    }
}

impl Drop for SidecarClient {
    fn drop(&mut self) {
        let _ = self._child.kill();
        let _ = self._child.wait();
    }
}

struct DesktopState {
    sidecar: Mutex<Option<SidecarClient>>,
}

fn locate_sidecar() -> Option<PathBuf> {
    let suffix = "psyche-os-sidecar-x86_64-pc-windows-msvc.exe";
    let mut candidates = Vec::new();
    if let Ok(executable) = std::env::current_exe() {
        if let Some(directory) = executable.parent() {
            candidates.push(directory.join("psyche-os-sidecar.exe"));
            candidates.push(directory.join(suffix));
            candidates.push(directory.join("binaries").join(suffix));
        }
    }
    candidates.push(
        Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("binaries")
            .join(suffix),
    );
    candidates.into_iter().find(|candidate| candidate.is_file())
}

fn sanitize_code(code: &str) -> String {
    if !code.is_empty()
        && code.len() <= 64
        && code
            .chars()
            .all(|value| value.is_ascii_uppercase() || value == '_')
    {
        code.to_string()
    } else {
        "OPERATION_FAILED".to_string()
    }
}

fn allowed_origin(window: &WebviewWindow) -> bool {
    if window.label() != "main" {
        return false;
    }
    window.url().is_ok_and(|url| {
        let host = url.host_str().unwrap_or_default();
        ALLOWED_ORIGINS
            .iter()
            .any(|(scheme, allowed_host)| url.scheme() == *scheme && host == *allowed_host)
    })
}

fn invoke_python(
    window: &WebviewWindow,
    state: &tauri::State<'_, DesktopState>,
    command: &'static str,
    session_token: Option<&str>,
    payload: Value,
) -> Result<Value, String> {
    if !allowed_origin(window) {
        return Err("ORIGIN_REJECTED".to_string());
    }
    let mut guard = state
        .sidecar
        .lock()
        .map_err(|_| "SIDECAR_UNAVAILABLE".to_string())?;
    if guard.is_none() {
        *guard = Some(SidecarClient::spawn()?);
    }
    guard
        .as_mut()
        .ok_or_else(|| "SIDECAR_UNAVAILABLE".to_string())?
        .invoke(command, session_token, payload)
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct SessionRequest {
    session_token: Option<String>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct UnlockRequest {
    secret: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct CorrectionRequest {
    session_token: Option<String>,
    record_id: String,
    replacement: String,
    reason: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct RecordRequest {
    session_token: Option<String>,
    record_id: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct DeletionRequest {
    session_token: Option<String>,
    plan_id: String,
    confirmation: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct RecoveryRequest {
    session_token: Option<String>,
    candidate_id: String,
    confirmation: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct ExportPreviewRequest {
    session_token: Option<String>,
    purpose: String,
    audience: String,
    scope: String,
    encrypted: bool,
    redacted: bool,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct ExportExecuteRequest {
    session_token: Option<String>,
    preview_id: String,
    confirmation: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct ArchiveOperationRequest {
    session_token: Option<String>,
    operation: String,
    choice: String,
    idempotency_key: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct TimelineRequest {
    session_token: Option<String>,
    temporal_role: String,
}

fn bounded(values: &[&str]) -> Result<(), String> {
    if values
        .iter()
        .all(|value| !value.trim().is_empty() && value.len() <= MAX_TEXT)
    {
        Ok(())
    } else {
        Err("INVALID_PAYLOAD".to_string())
    }
}

#[tauri::command]
fn desktop_status(
    window: WebviewWindow,
    state: tauri::State<'_, DesktopState>,
) -> Result<Value, String> {
    invoke_python(&window, &state, "status.get", None, json!({}))
}

#[tauri::command]
fn desktop_unlock(
    window: WebviewWindow,
    state: tauri::State<'_, DesktopState>,
    request: UnlockRequest,
) -> Result<Value, String> {
    if request.secret.is_empty() || request.secret.len() > 256 {
        return Err("UNLOCK_REJECTED".to_string());
    }
    invoke_python(
        &window,
        &state,
        "session.unlock",
        None,
        json!({ "secret": request.secret }),
    )
}

#[tauri::command]
fn desktop_lock(
    window: WebviewWindow,
    state: tauri::State<'_, DesktopState>,
    request: SessionRequest,
) -> Result<Value, String> {
    invoke_python(
        &window,
        &state,
        "session.lock",
        request.session_token.as_deref(),
        json!({}),
    )
}

#[tauri::command]
fn desktop_correct(
    window: WebviewWindow,
    state: tauri::State<'_, DesktopState>,
    request: CorrectionRequest,
) -> Result<Value, String> {
    bounded(&[&request.record_id, &request.replacement, &request.reason])?;
    invoke_python(
        &window,
        &state,
        "correction.apply",
        request.session_token.as_deref(),
        json!({ "record_id": request.record_id, "replacement": request.replacement, "reason": request.reason }),
    )
}

#[tauri::command]
fn desktop_plan_deletion(
    window: WebviewWindow,
    state: tauri::State<'_, DesktopState>,
    request: RecordRequest,
) -> Result<Value, String> {
    bounded(&[&request.record_id])?;
    invoke_python(
        &window,
        &state,
        "deletion.plan",
        request.session_token.as_deref(),
        json!({ "record_id": request.record_id }),
    )
}

#[tauri::command]
fn desktop_execute_deletion(
    window: WebviewWindow,
    state: tauri::State<'_, DesktopState>,
    request: DeletionRequest,
) -> Result<Value, String> {
    bounded(&[&request.plan_id, &request.confirmation])?;
    invoke_python(
        &window,
        &state,
        "deletion.execute",
        request.session_token.as_deref(),
        json!({ "plan_id": request.plan_id, "confirmation": request.confirmation }),
    )
}

macro_rules! session_command {
    ($name:ident, $command:literal) => {
        #[tauri::command]
        fn $name(
            window: WebviewWindow,
            state: tauri::State<'_, DesktopState>,
            request: SessionRequest,
        ) -> Result<Value, String> {
            invoke_python(
                &window,
                &state,
                $command,
                request.session_token.as_deref(),
                json!({}),
            )
        }
    };
}

session_command!(desktop_backup_status, "backup.status");
session_command!(desktop_verify_backup, "backup.verify");
session_command!(desktop_validate_recovery, "recovery.validate");
session_command!(desktop_archive_explorer, "archive.explorer");
session_command!(desktop_archive_snapshot_diff, "archive.snapshot_diff");

#[tauri::command]
fn desktop_archive_operate(
    window: WebviewWindow,
    state: tauri::State<'_, DesktopState>,
    request: ArchiveOperationRequest,
) -> Result<Value, String> {
    bounded(&[
        &request.operation,
        &request.choice,
        &request.idempotency_key,
    ])?;
    invoke_python(
        &window,
        &state,
        "archive.operate",
        request.session_token.as_deref(),
        json!({ "operation": request.operation, "choice": request.choice, "idempotency_key": request.idempotency_key }),
    )
}

#[tauri::command]
fn desktop_archive_timeline(
    window: WebviewWindow,
    state: tauri::State<'_, DesktopState>,
    request: TimelineRequest,
) -> Result<Value, String> {
    bounded(&[&request.temporal_role])?;
    invoke_python(
        &window,
        &state,
        "archive.timeline",
        request.session_token.as_deref(),
        json!({ "temporal_role": request.temporal_role }),
    )
}

#[tauri::command]
fn desktop_archive_execute_deletion(
    window: WebviewWindow,
    state: tauri::State<'_, DesktopState>,
    request: DeletionRequest,
) -> Result<Value, String> {
    bounded(&[&request.plan_id, &request.confirmation])?;
    invoke_python(
        &window,
        &state,
        "archive.deletion.execute",
        request.session_token.as_deref(),
        json!({ "plan_id": request.plan_id, "confirmation": request.confirmation }),
    )
}

#[tauri::command]
fn desktop_activate_recovery(
    window: WebviewWindow,
    state: tauri::State<'_, DesktopState>,
    request: RecoveryRequest,
) -> Result<Value, String> {
    bounded(&[&request.candidate_id, &request.confirmation])?;
    invoke_python(
        &window,
        &state,
        "recovery.activate",
        request.session_token.as_deref(),
        json!({ "candidate_id": request.candidate_id, "confirmation": request.confirmation }),
    )
}

#[tauri::command]
fn desktop_preview_export(
    window: WebviewWindow,
    state: tauri::State<'_, DesktopState>,
    request: ExportPreviewRequest,
) -> Result<Value, String> {
    bounded(&[&request.purpose, &request.audience, &request.scope])?;
    invoke_python(
        &window,
        &state,
        "export.preview",
        request.session_token.as_deref(),
        json!({ "purpose": request.purpose, "audience": request.audience, "scope": request.scope, "encrypted": request.encrypted, "redacted": request.redacted }),
    )
}

#[tauri::command]
fn desktop_execute_export(
    window: WebviewWindow,
    state: tauri::State<'_, DesktopState>,
    request: ExportExecuteRequest,
) -> Result<Value, String> {
    bounded(&[&request.preview_id, &request.confirmation])?;
    invoke_python(
        &window,
        &state,
        "export.execute",
        request.session_token.as_deref(),
        json!({ "preview_id": request.preview_id, "confirmation": request.confirmation }),
    )
}

pub fn run() {
    tauri::Builder::default()
        .manage(DesktopState {
            sidecar: Mutex::new(None),
        })
        .invoke_handler(tauri::generate_handler![
            desktop_status,
            desktop_unlock,
            desktop_lock,
            desktop_correct,
            desktop_plan_deletion,
            desktop_execute_deletion,
            desktop_backup_status,
            desktop_verify_backup,
            desktop_validate_recovery,
            desktop_activate_recovery,
            desktop_preview_export,
            desktop_execute_export,
            desktop_archive_operate,
            desktop_archive_timeline,
            desktop_archive_explorer,
            desktop_archive_snapshot_diff,
            desktop_archive_execute_deletion
        ])
        .setup(|app| {
            WebviewWindowBuilder::new(app, "main", WebviewUrl::App("index.html".into()))
                .title("PSYCHE OS — Управление локальным хранилищем")
                .inner_size(1180.0, 820.0)
                .min_inner_size(760.0, 640.0)
                .devtools(false)
                .additional_browser_args(
                    "--disable-features=msWebOOUI,msPdfOOUI,msSmartScreenProtection \
                     --disable-background-networking \
                     --host-resolver-rules=MAP * ~NOTFOUND \
                     --force-renderer-accessibility",
                )
                .on_new_window(|_, _| tauri::webview::NewWindowResponse::Deny)
                .on_navigation(|url| {
                    let host = url.host_str().unwrap_or_default();
                    ALLOWED_ORIGINS.iter().any(|(scheme, allowed_host)| {
                        url.scheme() == *scheme && host == *allowed_host
                    })
                })
                .build()?;
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("desktop runtime failed");
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn t2_strict_requests_reject_unknown_fields() {
        let value = json!({ "sessionToken": "opaque", "extra": "cmd.exe" });
        assert!(serde_json::from_value::<SessionRequest>(value).is_err());
    }

    #[test]
    fn t3_raw_error_text_is_reduced_to_content_free_code() {
        assert_eq!(
            sanitize_code("C:/vault/private.db: secret"),
            "OPERATION_FAILED"
        );
        assert_eq!(sanitize_code("SESSION_REQUIRED"), "SESSION_REQUIRED");
    }

    #[test]
    fn t2_sidecar_path_is_fixed_and_not_renderer_supplied() {
        let path = locate_sidecar();
        if let Some(path) = path {
            assert!(path
                .file_name()
                .is_some_and(|name| name.to_string_lossy().starts_with("psyche-os-sidecar")));
        }
    }

    #[test]
    fn t1_only_packaged_local_origins_are_allowed() {
        for rejected in [
            "https://example.com",
            "http://127.0.0.1:8000",
            "file:///C:/vault/private.db",
        ] {
            let url = url::Url::parse(rejected).expect("valid test URL");
            let host = url.host_str().unwrap_or_default();
            assert!(!ALLOWED_ORIGINS
                .iter()
                .any(|(scheme, allowed_host)| url.scheme() == *scheme && host == *allowed_host));
        }
    }

    #[test]
    fn t1_renderer_capability_excludes_tauri_core_default() {
        let capability = include_str!("../capabilities/main-local.json");
        let value: Value = serde_json::from_str(capability).expect("valid capability JSON");
        let permissions = value["permissions"]
            .as_array()
            .expect("capability permissions array");
        assert!(!permissions.iter().any(|permission| {
            permission
                .as_str()
                .is_some_and(|identifier| identifier.starts_with("core:"))
        }));
    }

    #[test]
    fn t2_payload_limit_rejects_oversized_text() {
        assert_eq!(
            bounded(&[&"x".repeat(MAX_TEXT + 1)]),
            Err("INVALID_PAYLOAD".to_string())
        );
    }
}

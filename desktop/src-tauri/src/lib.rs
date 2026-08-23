#![deny(unsafe_code)]

#[allow(dead_code)]
mod command_manifest;

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
const MAX_TURN_TEXT: usize = 12_000;
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
        let app_data = std::env::var_os("PSYCHE_OS_APP_DATA")
            .map(PathBuf::from)
            .or_else(|| std::env::var_os("LOCALAPPDATA").map(|base| PathBuf::from(base).join("PSYCHE OS")))
            .ok_or_else(|| "SIDECAR_UNAVAILABLE".to_string())?;
        std::fs::create_dir_all(&app_data).map_err(|_| "SIDECAR_UNAVAILABLE".to_string())?;
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
            .env("PSYCHE_OS_APP_DATA", app_data)
            // Deliberately forward only the provider credential; renderer input
            // cannot influence the sidecar environment or destination.
            .env("OPENAI_API_KEY", std::env::var("OPENAI_API_KEY").unwrap_or_default())
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
        && code.chars().count() <= 64
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

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct ReflectionCreateRequest { session_token: Option<String>, title: String }
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct ReflectionSessionRequest { session_token: Option<String>, session_id: String }
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct ReflectionTurnRequest { session_token: Option<String>, session_id: String, content: String }
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct ReflectionDeleteRequest { session_token: Option<String>, session_id: String, confirmation: String }
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct ExplorationAnswerRequest { session_token: Option<String>, question_id: String, answer_text: String }
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct FormulationCorrectionRequest { session_token: Option<String>, formulation_id: String, correction_text: String }
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct FormulationRequest { session_token: Option<String>, formulation_id: String }
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct ExplorationQuestionRequest { session_token: Option<String>, question_id: String }
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct ActionOptionsRequest { session_token: Option<String>, session_id: String, anchor_type: Option<String>, anchor_id: Option<String> }
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct ActionCreateRequest { session_token: Option<String>, session_id: String, user_goal: String, template_id: String, action_text: String, anchor_type: Option<String>, anchor_id: Option<String> }
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct ActionOutcomeRequest { session_token: Option<String>, plan_id: String, status: String, note_text: Option<String> }
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct AiExecuteRequest { session_token: Option<String>, preview_id: String, opt_in: bool }
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct AiSelectionItem { record_id: String, role: String }
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct AiPrepareRequest { session_token: Option<String>, selected: Vec<AiSelectionItem> }
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct ReflectionSearchRequest { session_token: Option<String>, query: String, state: String, limit: u32, offset: u32 }

fn bounded(values: &[&str]) -> Result<(), String> {
    if values
        .iter()
        .all(|value| !value.trim().is_empty() && value.chars().count() <= MAX_TEXT)
    {
        Ok(())
    } else {
        Err("INVALID_PAYLOAD".to_string())
    }
}

fn bounded_turn(value: &str) -> Result<(), String> {
    if !value.trim().is_empty() && value.chars().count() <= MAX_TURN_TEXT { Ok(()) } else { Err("INVALID_PAYLOAD".to_string()) }
}

fn bounded_search_query(query: &str) -> Result<(), String> {
    if !query.trim().is_empty() && query.chars().count() <= 200 { Ok(()) } else { Err("INVALID_PAYLOAD".to_string()) }
}

#[tauri::command]
fn desktop_reflection_create(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: ReflectionCreateRequest) -> Result<Value, String> {
    bounded(&[&request.title])?;
    invoke_python(&window, &state, "reflection_session.create", request.session_token.as_deref(), json!({"title": request.title}))
}
#[tauri::command]
fn desktop_reflection_list(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: SessionRequest) -> Result<Value, String> {
    invoke_python(&window, &state, "reflection_session.list", request.session_token.as_deref(), json!({}))
}
#[tauri::command]
fn desktop_reflection_get(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: ReflectionSessionRequest) -> Result<Value, String> {
    bounded(&[&request.session_id])?;
    invoke_python(&window, &state, "reflection_session.get", request.session_token.as_deref(), json!({"session_id": request.session_id}))
}
#[tauri::command]
fn desktop_reflection_add_turn(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: ReflectionTurnRequest) -> Result<Value, String> {
    bounded(&[&request.session_id])?; bounded_turn(&request.content)?;
    invoke_python(&window, &state, "reflection_session.add_turn", request.session_token.as_deref(), json!({"session_id": request.session_id, "content": request.content}))
}
#[tauri::command]
fn desktop_reflection_close(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: ReflectionSessionRequest) -> Result<Value, String> {
    bounded(&[&request.session_id])?;
    invoke_python(&window, &state, "reflection_session.close", request.session_token.as_deref(), json!({"session_id": request.session_id}))
}
#[tauri::command]
fn desktop_reflection_delete(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: ReflectionDeleteRequest) -> Result<Value, String> {
    bounded(&[&request.session_id, &request.confirmation])?;
    invoke_python(&window, &state, "reflection_session.delete", request.session_token.as_deref(), json!({"session_id": request.session_id, "confirmation": request.confirmation}))
}
#[tauri::command]
fn desktop_exploration_start(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: ReflectionSessionRequest) -> Result<Value, String> {
    bounded(&[&request.session_id])?;
    invoke_python(&window, &state, "reflection_exploration.start", request.session_token.as_deref(), json!({"session_id": request.session_id}))
}
#[tauri::command]
fn desktop_exploration_get(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: ReflectionSessionRequest) -> Result<Value, String> {
    bounded(&[&request.session_id])?;
    invoke_python(&window, &state, "reflection_exploration.get", request.session_token.as_deref(), json!({"session_id": request.session_id}))
}
#[tauri::command]
fn desktop_exploration_answer(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: ExplorationAnswerRequest) -> Result<Value, String> {
    bounded(&[&request.question_id])?; bounded_turn(&request.answer_text)?;
    invoke_python(&window, &state, "reflection_exploration.answer", request.session_token.as_deref(), json!({"question_id": request.question_id, "answer_text": request.answer_text}))
}
#[tauri::command]
fn desktop_exploration_skip(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: ExplorationQuestionRequest) -> Result<Value, String> {
    bounded(&[&request.question_id])?;
    invoke_python(&window, &state, "reflection_exploration.skip", request.session_token.as_deref(), json!({"question_id": request.question_id}))
}
#[tauri::command]
fn desktop_formulation_propose(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: ReflectionSessionRequest) -> Result<Value, String> {
    bounded(&[&request.session_id])?;
    invoke_python(&window, &state, "reflection_exploration.formulation.propose", request.session_token.as_deref(), json!({"session_id": request.session_id}))
}
#[tauri::command]
fn desktop_formulation_correct(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: FormulationCorrectionRequest) -> Result<Value, String> {
    bounded(&[&request.formulation_id, &request.correction_text])?;
    invoke_python(&window, &state, "reflection_exploration.formulation.correct", request.session_token.as_deref(), json!({"formulation_id": request.formulation_id, "correction_text": request.correction_text}))
}
#[tauri::command]
fn desktop_formulation_accept(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: FormulationRequest) -> Result<Value, String> {
    bounded(&[&request.formulation_id])?;
    invoke_python(&window, &state, "reflection_exploration.formulation.accept", request.session_token.as_deref(), json!({"formulation_id": request.formulation_id}))
}
#[tauri::command]
fn desktop_formulation_reject(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: FormulationRequest) -> Result<Value, String> {
    bounded(&[&request.formulation_id])?;
    invoke_python(&window, &state, "reflection_exploration.formulation.reject", request.session_token.as_deref(), json!({"formulation_id": request.formulation_id}))
}
#[tauri::command]
fn desktop_action_options(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: ActionOptionsRequest) -> Result<Value, String> {
    bounded(&[&request.session_id])?;
    if let Some(anchor_type) = &request.anchor_type { bounded(&[anchor_type])?; }
    if let Some(anchor_id) = &request.anchor_id { bounded(&[anchor_id])?; }
    invoke_python(&window, &state, "reflection_action.options", request.session_token.as_deref(), json!({"session_id": request.session_id, "anchor_type": request.anchor_type, "anchor_id": request.anchor_id}))
}
#[tauri::command]
fn desktop_action_list(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: ReflectionSessionRequest) -> Result<Value, String> {
    bounded(&[&request.session_id])?;
    invoke_python(&window, &state, "reflection_action.list", request.session_token.as_deref(), json!({"session_id": request.session_id}))
}
#[tauri::command]
fn desktop_action_create(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: ActionCreateRequest) -> Result<Value, String> {
    bounded(&[&request.session_id, &request.template_id])?; bounded_turn(&request.user_goal)?; bounded_turn(&request.action_text)?;
    if let Some(anchor_type) = &request.anchor_type { bounded(&[anchor_type])?; }
    if let Some(anchor_id) = &request.anchor_id { bounded(&[anchor_id])?; }
    invoke_python(&window, &state, "reflection_action.create", request.session_token.as_deref(), json!({"session_id": request.session_id, "user_goal": request.user_goal, "template_id": request.template_id, "action_text": request.action_text, "anchor_type": request.anchor_type, "anchor_id": request.anchor_id}))
}
#[tauri::command]
fn desktop_action_record_outcome(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: ActionOutcomeRequest) -> Result<Value, String> {
    bounded(&[&request.plan_id, &request.status])?;
    if let Some(note_text) = &request.note_text { bounded_turn(note_text)?; }
    invoke_python(&window, &state, "reflection_action.record_outcome", request.session_token.as_deref(), json!({"plan_id": request.plan_id, "status": request.status, "note_text": request.note_text}))
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

session_command!(desktop_ai_status, "ai.status");
session_command!(desktop_ai_list_eligible, "ai.list_eligible");
#[tauri::command]
fn desktop_ai_prepare(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: AiPrepareRequest) -> Result<Value, String> {
    if request.selected.is_empty() || request.selected.len() > 8 {
        return Err("INVALID_PAYLOAD".to_string());
    }
    for item in &request.selected {
        bounded(&[&item.record_id])?;
        if !matches!(item.role.as_str(), "supporting" | "counterevidence" | "unknown") {
            return Err("INVALID_PAYLOAD".to_string());
        }
    }
    let selected: Vec<Value> = request
        .selected
        .iter()
        .map(|item| json!({"record_id": item.record_id, "role": item.role}))
        .collect();
    invoke_python(&window, &state, "ai.prepare", request.session_token.as_deref(), json!({"selected": selected}))
}
#[tauri::command]
fn desktop_ai_authorize_execute(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: AiExecuteRequest) -> Result<Value, String> {
    bounded(&[&request.preview_id])?;
    invoke_python(&window, &state, "ai.authorize_execute", request.session_token.as_deref(), json!({"preview_id": request.preview_id, "opt_in": request.opt_in}))
}
#[tauri::command]
fn desktop_reflection_search(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: ReflectionSearchRequest) -> Result<Value, String> {
    bounded_search_query(&request.query)?;
    if !matches!(request.state.as_str(), "ALL" | "ACTIVE" | "CLOSED") {
        return Err("INVALID_PAYLOAD".to_string());
    }
    if !(1..=50).contains(&request.limit) {
        return Err("INVALID_PAYLOAD".to_string());
    }
    invoke_python(&window, &state, "reflection.search", request.session_token.as_deref(), json!({"query": request.query, "state": request.state, "limit": request.limit, "offset": request.offset}))
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
            ,desktop_ai_status, desktop_ai_list_eligible, desktop_ai_prepare, desktop_ai_authorize_execute
            ,desktop_reflection_create, desktop_reflection_list, desktop_reflection_get,
            desktop_reflection_add_turn, desktop_reflection_close, desktop_reflection_delete,
            desktop_reflection_search,
            desktop_exploration_start, desktop_exploration_get, desktop_exploration_answer, desktop_exploration_skip,
            desktop_formulation_propose, desktop_formulation_correct, desktop_formulation_accept, desktop_formulation_reject,
            desktop_action_options, desktop_action_list, desktop_action_create, desktop_action_record_outcome
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
    use std::collections::BTreeSet;

    #[test]
    fn t2_strict_requests_reject_unknown_fields() {
        let value = json!({ "sessionToken": "opaque", "extra": "cmd.exe" });
        assert!(serde_json::from_value::<SessionRequest>(value).is_err());
    }

    #[test]
    fn t2_nested_ai_selection_accepts_only_renderer_camel_case() {
        let camel_case = json!({"sessionToken": "opaque", "selected": [{"recordId": "record-1", "role": "supporting"}]});
        let request = serde_json::from_value::<AiPrepareRequest>(camel_case).expect("camelCase renderer request must deserialize");
        assert_eq!(request.selected[0].record_id, "record-1");
        let snake_case = json!({"sessionToken": "opaque", "selected": [{"record_id": "record-1", "role": "supporting"}]});
        assert!(serde_json::from_value::<AiPrepareRequest>(snake_case).is_err());
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
    fn t1_native_command_manifest_matches_handlers_capability_and_renderer_api() {
        let library_source = include_str!("lib.rs");
        let handler_block = library_source.split_once(".invoke_handler(tauri::generate_handler![").and_then(|(_, tail)| tail.split_once("])")).map(|(block, _)| block).expect("generate_handler block");
        let capability: Value = serde_json::from_str(include_str!("../capabilities/main-local.json")).expect("valid capability JSON");
        let actual_permissions: BTreeSet<String> = capability["permissions"].as_array().expect("capability permissions array").iter().map(|permission| permission.as_str().expect("string capability permission").to_string()).collect();
        let expected_permissions: BTreeSet<String> = command_manifest::SHIPPED_COMMANDS.iter().map(|command| format!("allow-{}", command.replace('_', "-"))).collect();
        assert_eq!(actual_permissions, expected_permissions);
        let renderer_api = include_str!("../../src/api.ts");
        for command in command_manifest::SHIPPED_COMMANDS {
            assert!(handler_block.contains(command), "{command} is absent from generate_handler");
            assert!(renderer_api.contains(&format!("\"{command}\"")), "{command} is absent from renderer API");
        }
        assert!(include_str!("../build.rs").contains("commands(command_manifest::SHIPPED_COMMANDS)"));
    }

    #[test]
    fn t2_payload_limit_rejects_oversized_text() {
        assert_eq!(
            bounded(&[&"x".repeat(MAX_TEXT + 1)]),
            Err("INVALID_PAYLOAD".to_string())
        );
    }

    #[test]
    fn t2_user_text_limits_count_unicode_characters_not_utf8_bytes() {
        let exact_cyrillic = "\u{044f}".repeat(MAX_TEXT);
        assert_eq!(bounded(&[&exact_cyrillic]), Ok(()));
        assert_eq!(bounded(&[&format!("{exact_cyrillic}\u{044f}")]), Err("INVALID_PAYLOAD".to_string()));
        let exact_search = "\u{1f9ed}".repeat(200);
        assert_eq!(bounded_search_query(&exact_search), Ok(()));
        assert_eq!(bounded_search_query(&format!("{exact_search}\u{1f9ed}")), Err("INVALID_PAYLOAD".to_string()));
    }
}

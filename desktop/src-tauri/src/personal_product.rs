//! Separate Personal desktop product.  This module is the entire Rust command
//! surface compiled with `personal-product`; it has no synthetic command table.

use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::ffi::OsString;
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
// `build.rs` always supplies these values. Release Personal builds refuse to
// compile unless both are exact lower-case hexadecimal identities.
const PERSONAL_BUILD_ID: &str = env!("PSYCHE_OS_PERSONAL_BUILD_ID");
const PERSONAL_PROFILE_DIGEST: &str = env!("PSYCHE_OS_PERSONAL_PROFILE_DIGEST");
const PERSONAL_PROFILE_ID: &str = env!("PSYCHE_OS_PERSONAL_PROFILE_ID");

#[derive(Serialize)]
struct Request<'a> { version: &'static str, command: &'static str, correlation_id: String, session_token: Option<&'a str>, payload: Value }
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Response { version: String, correlation_id: String, status: String, #[serde(default)] data: Option<Value>, #[serde(default)] error: Option<ErrorResponse> }
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct ErrorResponse { code: String }

struct PersonalSidecar { _child: Child, stdin: ChildStdin, stdout: BufReader<ChildStdout> }

impl PersonalSidecar {
    fn spawn() -> Result<Self, String> {
        let path = locate_personal_sidecar().ok_or_else(|| "SIDECAR_UNAVAILABLE".to_string())?;
        let local_data = std::env::var_os("LOCALAPPDATA").map(PathBuf::from).ok_or_else(|| "SIDECAR_UNAVAILABLE".to_string())?;
        Self::spawn_at(path, local_data)
    }

    fn spawn_at(path: PathBuf, local_data: PathBuf) -> Result<Self, String> {
        let temp = std::env::temp_dir();
        let mut child = Command::new(path).stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::null()).env_clear()
            .envs(personal_environment(&temp, &local_data)).spawn().map_err(|_| "SIDECAR_UNAVAILABLE".to_string())?;
        Ok(Self { stdin: child.stdin.take().ok_or_else(|| "SIDECAR_UNAVAILABLE".to_string())?, stdout: BufReader::new(child.stdout.take().ok_or_else(|| "SIDECAR_UNAVAILABLE".to_string())?), _child: child })
    }

    #[cfg(test)]
    fn spawn_admitted_test_fixture(local_data: PathBuf) -> Result<Self, String> {
        let fixture = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../tests/fixtures/personal_admitted_sidecar.py");
        let python = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../.venv/Scripts/python.exe");
        let source = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../src");
        let mut child = Command::new(python).arg(fixture).stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::null()).env_clear()
            .envs(personal_environment(&std::env::temp_dir(), &local_data)).env("PYTHONPATH", source).spawn().map_err(|_| "SIDECAR_UNAVAILABLE".to_string())?;
        Ok(Self { stdin: child.stdin.take().ok_or_else(|| "SIDECAR_UNAVAILABLE".to_string())?, stdout: BufReader::new(child.stdout.take().ok_or_else(|| "SIDECAR_UNAVAILABLE".to_string())?), _child: child })
    }

    fn invoke(&mut self, command: &'static str, session_token: Option<&str>, payload: Value) -> Result<Value, String> {
        let correlation_id = Uuid::new_v4().simple().to_string();
        let body = serde_json::to_vec(&Request { version: PROTOCOL_VERSION, command, correlation_id: correlation_id.clone(), session_token, payload }).map_err(|_| "REQUEST_INVALID".to_string())?;
        if body.is_empty() || body.len() > MAX_FRAME_BYTES { return Err("REQUEST_INVALID".to_string()); }
        self.stdin.write_all(&(body.len() as u32).to_be_bytes()).and_then(|_| self.stdin.write_all(&body)).and_then(|_| self.stdin.flush()).map_err(|_| "SIDECAR_IO_FAILED".to_string())?;
        let mut header = [0_u8; 4];
        self.stdout.read_exact(&mut header).map_err(|_| "SIDECAR_IO_FAILED".to_string())?;
        let length = u32::from_be_bytes(header) as usize;
        if length == 0 || length > MAX_FRAME_BYTES { return Err("SIDECAR_PROTOCOL_FAILED".to_string()); }
        let mut response_body = vec![0_u8; length];
        self.stdout.read_exact(&mut response_body).map_err(|_| "SIDECAR_IO_FAILED".to_string())?;
        let response: Response = serde_json::from_slice(&response_body).map_err(|_| "SIDECAR_PROTOCOL_FAILED".to_string())?;
        if response.version != PROTOCOL_VERSION || response.correlation_id != correlation_id { return Err("SIDECAR_PROTOCOL_FAILED".to_string()); }
        match response.status.as_str() {
            "ok" => response.data.ok_or_else(|| "SIDECAR_PROTOCOL_FAILED".to_string()),
            "error" => Err(sanitize_code(response.error.map(|error| error.code).as_deref().unwrap_or("OPERATION_FAILED"))),
            _ => Err("SIDECAR_PROTOCOL_FAILED".to_string()),
        }
    }
}
impl Drop for PersonalSidecar { fn drop(&mut self) { let _ = self._child.kill(); let _ = self._child.wait(); } }

fn personal_environment(temp: &Path, local_data: &Path) -> Vec<(OsString, OsString)> {
    // env_clear is intentional: Personal never inherits provider credentials,
    // proxy configuration, or a synthetic data root.
    vec![
        (OsString::from("SYSTEMROOT"), std::env::var_os("SYSTEMROOT").unwrap_or_default()),
        (OsString::from("WINDIR"), std::env::var_os("WINDIR").unwrap_or_default()),
        (OsString::from("TEMP"), temp.as_os_str().to_owned()),
        (OsString::from("TMP"), temp.as_os_str().to_owned()),
        (OsString::from("PSYCHE_OS_LOCAL_APP_DATA"), local_data.as_os_str().to_owned()),
        (OsString::from("PSYCHE_OS_PERSONAL_ADMISSION_ROOT"), local_data.join("PSYCHE OS").join("Personal").into_os_string()),
        (OsString::from("PSYCHE_OS_PERSONAL_BUILD_ID"), OsString::from(PERSONAL_BUILD_ID)),
        (OsString::from("PSYCHE_OS_PERSONAL_PROFILE_ID"), OsString::from(PERSONAL_PROFILE_ID)),
        (OsString::from("PSYCHE_OS_PERSONAL_PROFILE_DIGEST"), OsString::from(PERSONAL_PROFILE_DIGEST)),
    ]
}

fn locate_personal_sidecar() -> Option<PathBuf> {
    let suffix = "psyche-os-personal-sidecar-x86_64-pc-windows-msvc.exe";
    let mut candidates = Vec::new();
    if let Ok(executable) = std::env::current_exe() { if let Some(directory) = executable.parent() { candidates.extend([directory.join("psyche-os-personal-sidecar.exe"), directory.join(suffix), directory.join("binaries").join(suffix)]); } }
    candidates.push(Path::new(env!("CARGO_MANIFEST_DIR")).join("binaries").join(suffix));
    candidates.into_iter().find(|candidate| candidate.is_file())
}
fn sanitize_code(code: &str) -> String { if !code.is_empty() && code.chars().count() <= 64 && code.chars().all(|value| value.is_ascii_uppercase() || value == '_') { code.to_string() } else { "OPERATION_FAILED".to_string() } }
fn allowed_origin(window: &WebviewWindow) -> bool { window.label() == "main" && window.url().is_ok_and(|url| ALLOWED_ORIGINS.iter().any(|(scheme, host)| url.scheme() == *scheme && url.host_str().unwrap_or_default() == *host)) }

struct DesktopState { sidecar: Mutex<Option<PersonalSidecar>> }
fn personal_call(window: &WebviewWindow, state: &tauri::State<'_, DesktopState>, command: &'static str, token: Option<&str>, payload: Value) -> Result<Value, String> {
    if !allowed_origin(window) { return Err("ORIGIN_REJECTED".to_string()); }
    let mut sidecar = state.sidecar.lock().map_err(|_| "SIDECAR_UNAVAILABLE".to_string())?;
    if sidecar.is_none() { *sidecar = Some(PersonalSidecar::spawn()?); }
    sidecar.as_mut().ok_or_else(|| "SIDECAR_UNAVAILABLE".to_string())?.invoke(command, token, payload)
}
fn bounded(values: &[&str]) -> Result<(), String> { if values.iter().all(|value| !value.trim().is_empty() && value.chars().count() <= MAX_TEXT) { Ok(()) } else { Err("INVALID_PAYLOAD".to_string()) } }
fn bounded_turn(value: &str) -> Result<(), String> { if !value.trim().is_empty() && value.chars().count() <= MAX_TURN_TEXT { Ok(()) } else { Err("INVALID_PAYLOAD".to_string()) } }

#[derive(Deserialize)] #[serde(rename_all = "camelCase", deny_unknown_fields)] struct SessionRequest { session_token: Option<String> }
#[derive(Deserialize)] #[serde(deny_unknown_fields)] struct UnlockRequest { secret: String }
#[derive(Deserialize)] #[serde(rename_all = "camelCase", deny_unknown_fields)] struct ReflectionCreateRequest { session_token: Option<String>, title: String }
#[derive(Deserialize)] #[serde(rename_all = "camelCase", deny_unknown_fields)] struct ReflectionSessionRequest { session_token: Option<String>, session_id: String }
#[derive(Deserialize)] #[serde(rename_all = "camelCase", deny_unknown_fields)] struct ReflectionTurnRequest { session_token: Option<String>, session_id: String, content: String }
#[derive(Deserialize)] #[serde(rename_all = "camelCase", deny_unknown_fields)] struct ReflectionDeleteRequest { session_token: Option<String>, session_id: String, confirmation: String }
#[derive(Deserialize)] #[serde(rename_all = "camelCase", deny_unknown_fields)] struct ReflectionSearchRequest { session_token: Option<String>, query: String, state: String, content: Option<String>, period: Option<String>, formulation_status: Option<String>, limit: u32, offset: u32 }
#[derive(Deserialize)] #[serde(rename_all = "camelCase", deny_unknown_fields)] struct ExplorationQuestionRequest { session_token: Option<String>, question_id: String }
#[derive(Deserialize)] #[serde(rename_all = "camelCase", deny_unknown_fields)] struct ExplorationAnswerRequest { session_token: Option<String>, question_id: String, answer_text: String }
#[derive(Deserialize)] #[serde(rename_all = "camelCase", deny_unknown_fields)] struct FormulationRequest { session_token: Option<String>, formulation_id: String }
#[derive(Deserialize)] #[serde(rename_all = "camelCase", deny_unknown_fields)] struct FormulationCorrectionRequest { session_token: Option<String>, formulation_id: String, correction_text: String }
#[derive(Deserialize)] #[serde(rename_all = "camelCase", deny_unknown_fields)] struct PersonalSecretRequest { session_token: Option<String>, secret: String }
#[derive(Deserialize)] #[serde(rename_all = "camelCase", deny_unknown_fields)] struct PersonalRestoreRequest { session_token: Option<String>, backup_id: String, secret: String }
#[derive(Deserialize)] #[serde(rename_all = "camelCase", deny_unknown_fields)] struct AIKeyRequest { session_token: Option<String>, api_key: String }
#[derive(Deserialize)] #[serde(rename_all = "camelCase", deny_unknown_fields)] struct AIPreviewRequest { session_token: Option<String>, session_id: String, selected_turn_ids: Vec<String> }
#[derive(Deserialize)] #[serde(rename_all = "camelCase", deny_unknown_fields)] struct AIExecuteRequest { session_token: Option<String>, interaction_id: String, preview_id: String }
#[derive(Deserialize)] #[serde(rename_all = "camelCase", deny_unknown_fields)] struct InterviewSessionRequest { session_token: Option<String>, interview_session_id: String }
#[derive(Deserialize)] #[serde(rename_all = "camelCase", deny_unknown_fields)] struct InterviewStartRequest { session_token: Option<String>, owner_topic: Option<String> }
#[derive(Deserialize)] #[serde(rename_all = "camelCase", deny_unknown_fields)] struct InterviewPolicyRequest { session_token: Option<String>, enabled: bool }
#[derive(Deserialize)] #[serde(rename_all = "camelCase", deny_unknown_fields)] struct InterviewSubmitRequest { session_token: Option<String>, interview_session_id: String, client_submission_id: String, content: String }
#[derive(Deserialize)] #[serde(rename_all = "camelCase", deny_unknown_fields)] struct InterviewRetryRequest { session_token: Option<String>, interview_session_id: String, answer_turn_id: String }
#[derive(Deserialize)] #[serde(rename_all = "camelCase", deny_unknown_fields)] struct InterviewControlRequest { session_token: Option<String>, interview_session_id: String, action: String, topic: Option<String> }
#[derive(Deserialize)] #[serde(rename_all = "camelCase", deny_unknown_fields)] struct InterviewDisclosureRequest { session_token: Option<String>, attempt_id: String }

fn bind_trusted_build_id(mut status: Value) -> Result<Value, String> {
    let fields = status
        .as_object_mut()
        .ok_or_else(|| "SIDECAR_PROTOCOL_FAILED".to_string())?;
    fields.insert("build_id".to_string(), json!(PERSONAL_BUILD_ID));
    Ok(status)
}

#[tauri::command]
fn desktop_status(window: WebviewWindow, state: tauri::State<'_, DesktopState>) -> Result<Value, String> {
    bind_trusted_build_id(personal_call(&window, &state, "status.get", None, json!({}))?)
}
#[tauri::command] fn desktop_unlock(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: UnlockRequest) -> Result<Value, String> { if request.secret.is_empty() || request.secret.len() > 256 { return Err("UNLOCK_REJECTED".to_string()); } personal_call(&window, &state, "session.unlock", None, json!({"secret": request.secret})) }
#[tauri::command] fn desktop_lock(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: SessionRequest) -> Result<Value, String> { personal_call(&window, &state, "session.lock", request.session_token.as_deref(), json!({})) }
#[tauri::command] fn desktop_reflection_create(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: ReflectionCreateRequest) -> Result<Value, String> { bounded(&[&request.title])?; personal_call(&window, &state, "reflection_session.create", request.session_token.as_deref(), json!({"title": request.title})) }
#[tauri::command] fn desktop_reflection_list(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: SessionRequest) -> Result<Value, String> { personal_call(&window, &state, "reflection_session.list", request.session_token.as_deref(), json!({})) }
macro_rules! session_id_command { ($name:ident, $command:literal) => { #[tauri::command] fn $name(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: ReflectionSessionRequest) -> Result<Value, String> { bounded(&[&request.session_id])?; personal_call(&window, &state, $command, request.session_token.as_deref(), json!({"session_id": request.session_id})) } }; }
session_id_command!(desktop_reflection_get, "reflection_session.get"); session_id_command!(desktop_reflection_close, "reflection_session.close"); session_id_command!(desktop_exploration_start, "reflection_exploration.start"); session_id_command!(desktop_exploration_get, "reflection_exploration.get"); session_id_command!(desktop_formulation_propose, "reflection_exploration.formulation.propose");
#[tauri::command] fn desktop_reflection_add_turn(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: ReflectionTurnRequest) -> Result<Value, String> { bounded(&[&request.session_id])?; bounded_turn(&request.content)?; personal_call(&window, &state, "reflection_session.add_turn", request.session_token.as_deref(), json!({"session_id": request.session_id, "content": request.content})) }
#[tauri::command] fn desktop_reflection_delete(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: ReflectionDeleteRequest) -> Result<Value, String> { bounded(&[&request.session_id, &request.confirmation])?; personal_call(&window, &state, "reflection_session.delete", request.session_token.as_deref(), json!({"session_id": request.session_id, "confirmation": request.confirmation})) }
#[tauri::command] fn desktop_reflection_search(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: ReflectionSearchRequest) -> Result<Value, String> {
    bounded(&[&request.query])?;
    let content = request.content.unwrap_or_else(|| "ALL".to_string());
    let period = request.period.unwrap_or_else(|| "ALL".to_string());
    let formulation_status = request.formulation_status.unwrap_or_else(|| "ALL".to_string());
    if !matches!(request.state.as_str(), "ALL" | "ACTIVE" | "CLOSED")
        || !matches!(content.as_str(), "ALL" | "SOURCE" | "UNKNOWN" | "CONTRADICTION" | "FORMULATION")
        || !matches!(period.as_str(), "ALL" | "7D" | "30D")
        || !matches!(formulation_status.as_str(), "ALL" | "CURRENT" | "PROPOSED" | "REJECTED" | "SUPERSEDED")
        || !(1..=50).contains(&request.limit) { return Err("INVALID_PAYLOAD".to_string()); }
    personal_call(&window, &state, "reflection.search", request.session_token.as_deref(), json!({"query": request.query, "state": request.state, "content": content, "period": period, "formulation_status": formulation_status, "limit": request.limit, "offset": request.offset}))
}
#[tauri::command] fn desktop_exploration_answer(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: ExplorationAnswerRequest) -> Result<Value, String> { bounded(&[&request.question_id])?; bounded_turn(&request.answer_text)?; personal_call(&window, &state, "reflection_exploration.answer", request.session_token.as_deref(), json!({"question_id": request.question_id, "answer_text": request.answer_text})) }
#[tauri::command] fn desktop_exploration_skip(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: ExplorationQuestionRequest) -> Result<Value, String> { bounded(&[&request.question_id])?; personal_call(&window, &state, "reflection_exploration.skip", request.session_token.as_deref(), json!({"question_id": request.question_id})) }
macro_rules! formulation_command { ($name:ident, $command:literal) => { #[tauri::command] fn $name(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: FormulationRequest) -> Result<Value, String> { bounded(&[&request.formulation_id])?; personal_call(&window, &state, $command, request.session_token.as_deref(), json!({"formulation_id": request.formulation_id})) } }; }
formulation_command!(desktop_formulation_accept, "reflection_exploration.formulation.accept"); formulation_command!(desktop_formulation_reject, "reflection_exploration.formulation.reject");
#[tauri::command] fn desktop_formulation_correct(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: FormulationCorrectionRequest) -> Result<Value, String> { bounded(&[&request.formulation_id, &request.correction_text])?; personal_call(&window, &state, "reflection_exploration.formulation.correct", request.session_token.as_deref(), json!({"formulation_id": request.formulation_id, "correction_text": request.correction_text})) }
#[tauri::command] fn desktop_personal_backup(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: PersonalSecretRequest) -> Result<Value, String> { bounded(&[&request.secret])?; personal_call(&window, &state, "backup.create", request.session_token.as_deref(), json!({"secret": request.secret})) }
#[tauri::command] fn desktop_personal_restore_isolated(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: PersonalRestoreRequest) -> Result<Value, String> { bounded(&[&request.backup_id, &request.secret])?; personal_call(&window, &state, "recovery.restore_isolated", request.session_token.as_deref(), json!({"backup_id": request.backup_id, "secret": request.secret})) }
#[tauri::command] fn desktop_personal_export_owner(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: PersonalSecretRequest) -> Result<Value, String> { bounded(&[&request.secret])?; personal_call(&window, &state, "export.owner", request.session_token.as_deref(), json!({"secret": request.secret})) }
#[tauri::command] fn desktop_personal_rotate(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: PersonalSecretRequest) -> Result<Value, String> { bounded(&[&request.secret])?; personal_call(&window, &state, "rotation.rotate", request.session_token.as_deref(), json!({"secret": request.secret})) }
#[tauri::command] fn desktop_personal_recovery_status(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: SessionRequest) -> Result<Value, String> { personal_call(&window, &state, "recovery.status", request.session_token.as_deref(), json!({})) }
#[tauri::command] fn desktop_ai_provider_status(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: SessionRequest) -> Result<Value, String> { personal_call(&window, &state, "ai.provider.status", request.session_token.as_deref(), json!({})) }
#[tauri::command] fn desktop_ai_provider_configure(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: AIKeyRequest) -> Result<Value, String> { if request.api_key.len() > 512 { return Err("INVALID_PAYLOAD".to_string()); } personal_call(&window, &state, "ai.provider.configure", request.session_token.as_deref(), json!({"api_key": request.api_key})) }
#[tauri::command] fn desktop_ai_provider_delete(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: SessionRequest) -> Result<Value, String> { personal_call(&window, &state, "ai.provider.delete", request.session_token.as_deref(), json!({})) }
#[tauri::command] fn desktop_ai_formulation_prepare(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: AIPreviewRequest) -> Result<Value, String> { if request.selected_turn_ids.len() > 8 || request.selected_turn_ids.iter().any(|id| id.is_empty() || id.len() > MAX_TEXT) { return Err("INVALID_PAYLOAD".to_string()); } personal_call(&window, &state, "ai.working_formulation.prepare", request.session_token.as_deref(), json!({"session_id": request.session_id, "selected_turn_ids": request.selected_turn_ids})) }
#[tauri::command] fn desktop_ai_formulation_execute(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: AIExecuteRequest) -> Result<Value, String> { bounded(&[&request.interaction_id, &request.preview_id])?; personal_call(&window, &state, "ai.working_formulation.authorize_execute", request.session_token.as_deref(), json!({"interaction_id": request.interaction_id, "preview_id": request.preview_id})) }
#[tauri::command] fn desktop_ai_interview_status(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: SessionRequest) -> Result<Value, String> { personal_call(&window, &state, "ai.interview.status", request.session_token.as_deref(), json!({})) }
#[tauri::command] fn desktop_ai_interview_policy(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: InterviewPolicyRequest) -> Result<Value, String> { personal_call(&window, &state, "ai.interview.policy", request.session_token.as_deref(), json!({"enabled": request.enabled})) }
#[tauri::command] fn desktop_ai_interview_start(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: InterviewStartRequest) -> Result<Value, String> { if let Some(topic) = &request.owner_topic { bounded(&[topic])?; } personal_call(&window, &state, "ai.interview.start", request.session_token.as_deref(), json!({"owner_topic": request.owner_topic})) }
#[tauri::command] fn desktop_ai_interview_list(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: SessionRequest) -> Result<Value, String> { personal_call(&window, &state, "ai.interview.list", request.session_token.as_deref(), json!({})) }
macro_rules! interview_session_command { ($name:ident, $command:literal) => { #[tauri::command] fn $name(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: InterviewSessionRequest) -> Result<Value, String> { bounded(&[&request.interview_session_id])?; personal_call(&window, &state, $command, request.session_token.as_deref(), json!({"interview_session_id": request.interview_session_id})) } }; }
interview_session_command!(desktop_ai_interview_grant_consent, "ai.interview.grant_consent"); interview_session_command!(desktop_ai_interview_revoke_consent, "ai.interview.revoke_consent"); interview_session_command!(desktop_ai_interview_first_question, "ai.interview.first_question"); interview_session_command!(desktop_ai_interview_get, "ai.interview.get");
#[tauri::command] fn desktop_ai_interview_submit(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: InterviewSubmitRequest) -> Result<Value, String> { bounded(&[&request.interview_session_id, &request.client_submission_id])?; bounded_turn(&request.content)?; personal_call(&window, &state, "ai.interview.submit", request.session_token.as_deref(), json!({"interview_session_id": request.interview_session_id, "client_submission_id": request.client_submission_id, "content": request.content})) }
#[tauri::command] fn desktop_ai_interview_retry(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: InterviewRetryRequest) -> Result<Value, String> { bounded(&[&request.interview_session_id, &request.answer_turn_id])?; personal_call(&window, &state, "ai.interview.retry", request.session_token.as_deref(), json!({"interview_session_id": request.interview_session_id, "answer_turn_id": request.answer_turn_id})) }
#[tauri::command] fn desktop_ai_interview_control(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: InterviewControlRequest) -> Result<Value, String> { bounded(&[&request.interview_session_id, &request.action])?; if let Some(topic) = &request.topic { bounded(&[topic])?; } personal_call(&window, &state, "ai.interview.control", request.session_token.as_deref(), json!({"interview_session_id": request.interview_session_id, "action": request.action, "topic": request.topic})) }
#[tauri::command] fn desktop_ai_interview_disclosure(window: WebviewWindow, state: tauri::State<'_, DesktopState>, request: InterviewDisclosureRequest) -> Result<Value, String> { bounded(&[&request.attempt_id])?; personal_call(&window, &state, "ai.interview.disclosure", request.session_token.as_deref(), json!({"attempt_id": request.attempt_id})) }

pub fn run() {
    tauri::Builder::default().manage(DesktopState { sidecar: Mutex::new(None) }).invoke_handler(tauri::generate_handler![
        desktop_status, desktop_unlock, desktop_lock, desktop_reflection_create, desktop_reflection_list, desktop_reflection_get, desktop_reflection_add_turn, desktop_reflection_close, desktop_reflection_delete, desktop_reflection_search,
        desktop_exploration_start, desktop_exploration_get, desktop_exploration_answer, desktop_exploration_skip, desktop_formulation_propose, desktop_formulation_correct, desktop_formulation_accept, desktop_formulation_reject,
        desktop_personal_backup, desktop_personal_restore_isolated, desktop_personal_export_owner, desktop_personal_rotate, desktop_personal_recovery_status,
        desktop_ai_provider_status, desktop_ai_provider_configure, desktop_ai_provider_delete, desktop_ai_formulation_prepare, desktop_ai_formulation_execute,
        desktop_ai_interview_status, desktop_ai_interview_policy, desktop_ai_interview_start, desktop_ai_interview_list, desktop_ai_interview_grant_consent, desktop_ai_interview_revoke_consent, desktop_ai_interview_first_question, desktop_ai_interview_submit, desktop_ai_interview_retry, desktop_ai_interview_control, desktop_ai_interview_get, desktop_ai_interview_disclosure
    ]).setup(|app| { WebviewWindowBuilder::new(app, "main", WebviewUrl::App("index.html".into())).title("PSYCHE OS Personal").inner_size(1180.0, 780.0).min_inner_size(820.0, 600.0).devtools(false).build()?; Ok(()) }).run(tauri::generate_context!()).expect("Personal desktop host failed");
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::BTreeSet;
    #[test]
    fn personal_manifest_matches_only_personal_handler_and_renderer() {
        let source = include_str!("personal_product.rs");
        let handler = source.split_once("tauri::generate_handler![").and_then(|(_, rest)| rest.split_once("]")).expect("handler");
        let capability: Value = serde_json::from_str(include_str!("../capabilities/personal-local.json")).expect("capability");
        let actual: BTreeSet<String> = capability["permissions"].as_array().unwrap().iter().map(|v| v.as_str().unwrap().to_string()).collect();
        let expected: BTreeSet<String> = super::super::personal_command_manifest::SHIPPED_COMMANDS.iter().map(|name| format!("allow-{}", name.replace('_', "-"))).collect();
        assert_eq!(actual, expected);
        let renderer = include_str!("../../src/personal-api.ts");
        for command in super::super::personal_command_manifest::SHIPPED_COMMANDS { assert!(source.contains(command)); assert!(renderer.contains(&format!("\"{command}\""))); }
        for forbidden in ["desktop_archive_", "desktop_action_"] { assert!(!handler.0.contains(forbidden)); }
    }
    #[test] fn personal_environment_has_no_provider_credential() { assert!(!personal_environment(Path::new("C:\\temp"), Path::new("C:\\local")).iter().any(|(key, _)| key == "OPENAI_API_KEY")); }
    #[test] fn personal_environment_has_only_launcher_bound_admission_identity() {
        let values: BTreeSet<OsString> = personal_environment(Path::new("C:\\temp"), Path::new("C:\\local")).into_iter().map(|(key, _)| key).collect();
        for required in ["PSYCHE_OS_PERSONAL_ADMISSION_ROOT", "PSYCHE_OS_PERSONAL_BUILD_ID", "PSYCHE_OS_PERSONAL_PROFILE_ID", "PSYCHE_OS_PERSONAL_PROFILE_DIGEST"] { assert!(values.contains(&OsString::from(required))); }
    }
    #[test] fn personal_environment_uses_the_build_script_identity() {
        let identity: std::collections::BTreeMap<OsString, OsString> = personal_environment(Path::new("C:\\temp"), Path::new("C:\\local")).into_iter().collect();
        assert_eq!(identity.get(&OsString::from("PSYCHE_OS_PERSONAL_BUILD_ID")), Some(&OsString::from(std::env::var("PSYCHE_OS_PERSONAL_BUILD_ID").unwrap_or_else(|_| "UNBOUND".to_string()))));
        assert_eq!(identity.get(&OsString::from("PSYCHE_OS_PERSONAL_PROFILE_DIGEST")), Some(&OsString::from(std::env::var("PSYCHE_OS_PERSONAL_PROFILE_DIGEST").unwrap_or_else(|_| "UNBOUND".to_string()))));
    }
    #[test]
    fn trusted_launcher_build_id_overrides_sidecar_status_value() {
        let status = bind_trusted_build_id(json!({
            "build_id": "sidecar-must-not-control-this",
            "runtime_profile": "LOCAL_PERSONAL_BOUNDED_OPENAI",
            "real_data_gate": "OPEN"
        }))
        .expect("object status is accepted");
        assert_eq!(status["build_id"], PERSONAL_BUILD_ID);
        assert_eq!(status["runtime_profile"], "LOCAL_PERSONAL_BOUNDED_OPENAI");
        assert_eq!(status["real_data_gate"], "OPEN");
    }
    #[test]
    fn trusted_launcher_build_id_rejects_non_object_sidecar_status() {
        assert_eq!(
            bind_trusted_build_id(json!(["not-a-status-object"])),
            Err("SIDECAR_PROTOCOL_FAILED".to_string())
        );
    }
    #[test]
    fn personal_rust_to_sidecar_closed_boundary_is_content_free_and_rejects_ai() {
        let base = std::env::temp_dir().join(format!("psyche-os-personal-rust-e2e-{}", Uuid::new_v4()));
        std::fs::create_dir_all(&base).expect("test base");
        let personal_root = base.join("PSYCHE OS").join("Personal");
        let path = locate_personal_sidecar().expect("built Personal sidecar");
        let mut sidecar = PersonalSidecar::spawn_at(path, base.clone()).expect("Personal sidecar starts");
        let status = sidecar.invoke("status.get", None, json!({})).expect("closed status");
        assert_eq!(status["local_personal"], "NOT_ADMITTED");
        assert_eq!(status["real_data_gate"], "CLOSED");
        assert!(!personal_root.exists(), "closed launch created a Personal root");
        assert_eq!(sidecar.invoke("session.unlock", None, json!({"secret": "Synthetic-Recovery-2026!"})), Err("NOT_ADMITTED".to_string()));
        assert_eq!(sidecar.invoke("ai.status", None, json!({})), Err("UNKNOWN_COMMAND".to_string()));
        drop(sidecar);
        std::fs::remove_dir_all(base).expect("remove isolated test base");
    }
    #[test]
    fn personal_rust_to_test_admitted_sidecar_captures_searches_and_locks() {
        let base = std::env::temp_dir().join(format!("psyche-os-personal-admitted-e2e-{}", Uuid::new_v4()));
        std::fs::create_dir_all(&base).expect("test base");
        let mut sidecar = PersonalSidecar::spawn_admitted_test_fixture(base.clone()).expect("test-admitted fixture starts");
        let token = sidecar.invoke("session.unlock", None, json!({"secret": "Synthetic-Recovery-2026!"})).expect("admitted unlock")["session_token"].as_str().expect("token").to_string();
        let created = sidecar.invoke("reflection_session.create", Some(&token), json!({"title": "Synthetic quick capture"})).expect("create");
        let session_id = created["session_id"].as_str().expect("session id").to_string();
        let marker = "P1_SYNTHETIC_NEVER_CLOUD_SENTINEL";
        sidecar.invoke("reflection_session.add_turn", Some(&token), json!({"session_id": session_id, "content": marker})).expect("add USER turn");
        assert_eq!(sidecar.invoke("reflection_session.list", Some(&token), json!({})).expect("list")["sessions"].as_array().expect("sessions").len(), 1);
        assert_eq!(sidecar.invoke("reflection_session.get", Some(&token), json!({"session_id": session_id})).expect("get")["turns"][0]["content"], marker);
        assert!(sidecar.invoke("reflection.search", Some(&token), json!({"query": marker, "state": "ALL", "limit": 20, "offset": 0})).expect("search")["total_matches"].as_u64().expect("matches") >= 1);
        sidecar.invoke("session.lock", Some(&token), json!({})).expect("lock");
        assert_eq!(sidecar.invoke("reflection_session.list", Some(&token), json!({})), Err("SESSION_REQUIRED".to_string()));
        assert_eq!(sidecar.invoke("ai.status", Some(&token), json!({})), Err("UNKNOWN_COMMAND".to_string()));
        drop(sidecar);
        std::fs::remove_dir_all(base).expect("remove isolated test base");
    }
}

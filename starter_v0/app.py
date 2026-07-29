from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from chat import (
    ARTIFACTS_DIR,
    ROOT,
    now_iso,
    run_model_tool_loop,
    safe_slug,
    trim_history,
    write_transcript,
)
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version

st.set_page_config(page_title="Research Agent", page_icon="🔎", layout="wide")

TRANSCRIPTS_DIR = ROOT / "transcripts"
RUNS_DIR = ROOT / "runs"
PROMPT_FILES = sorted(p.name for p in ARTIFACTS_DIR.glob("system_prompt*.md"))


def get_provider(name: str):
    key = f"_provider_{name}"
    if key not in st.session_state:
        st.session_state[key] = make_provider(name)
    return st.session_state[key]


def init_session() -> None:
    st.session_state.setdefault("history", [])
    st.session_state.setdefault("display_turns", [])
    st.session_state.setdefault("transcript", None)
    st.session_state.setdefault("transcript_path", None)
    st.session_state.setdefault("artifact_version", None)
    st.session_state.setdefault("turn_index", 0)


def start_new_session(version: str, provider_name: str, model: str | None, system_prompt_path: Path, tools_path: Path) -> None:
    st.session_state["history"] = []
    st.session_state["display_turns"] = []
    st.session_state["turn_index"] = 0
    artifact_version = build_artifact_version(version, system_prompt_path, tools_path)
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    transcript_id = "_".join([safe_slug(version), safe_slug(provider_name), timestamp])
    transcript_path = TRANSCRIPTS_DIR / f"{transcript_id}.transcript.json"
    st.session_state["transcript"] = {
        "transcript_id": transcript_id,
        **artifact_version_dict(artifact_version),
        "provider": provider_name,
        "model": model,
        "system_prompt": str(system_prompt_path),
        "tools": str(tools_path),
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "turns": [],
    }
    st.session_state["transcript_path"] = transcript_path
    st.session_state["artifact_version"] = artifact_version


def render_tool_event(event: dict[str, Any]) -> None:
    result = event.get("result", {})
    status = "error" if isinstance(result, dict) and result.get("error") else "ok"
    icon = "❌" if status == "error" else "✅"
    label = f"🔧 {event['tool']}({json.dumps(event.get('args', {}), ensure_ascii=False)}) {icon}"
    with st.expander(label):
        st.json(event)
        items = result.get("items") if isinstance(result, dict) else None
        if isinstance(items, list):
            for item in items:
                gif = item.get("gif_url") if isinstance(item, dict) else None
                if gif:
                    st.image(gif, caption=item.get("title") or "", width=240)


def render_turn(turn: dict[str, Any]) -> None:
    with st.chat_message("user"):
        st.write(turn["user"])
    with st.chat_message("assistant"):
        st.write(turn.get("assistant_text") or "")
        for round_record in turn.get("rounds", []):
            st.caption(f"round {round_record['round']}")
            for event in round_record.get("tool_results", []):
                render_tool_event(event)
        av = st.session_state.get("artifact_version")
        av_label = av.artifact_version if av else "?"
        st.caption(f"status={turn.get('status')} · version={av_label}")


def sidebar() -> tuple[str, str, str | None, Path, Path, int, int]:
    st.sidebar.header("Agent config")
    provider_name = st.sidebar.selectbox("Provider", ["openrouter", "openai", "anthropic", "gemini"])
    version = st.sidebar.text_input("Version label", value="v3")
    default_prompt = "system_prompt.md" if "system_prompt.md" in PROMPT_FILES else (PROMPT_FILES[0] if PROMPT_FILES else "system_prompt.md")
    system_prompt_name = st.sidebar.selectbox("System prompt", PROMPT_FILES, index=PROMPT_FILES.index(default_prompt))
    model = st.sidebar.text_input("Model override (optional)", value="")
    history_window = st.sidebar.slider("History window (turn pairs)", 1, 10, 5)
    max_tool_rounds = st.sidebar.slider("Max tool rounds", 1, 8, 4)

    system_prompt_path = ARTIFACTS_DIR / system_prompt_name
    tools_path = ARTIFACTS_DIR / "tools.yaml"

    if st.sidebar.button("Start / reset session", use_container_width=True):
        start_new_session(version, provider_name, model or None, system_prompt_path, tools_path)
        st.rerun()

    av = st.session_state.get("artifact_version")
    if av:
        st.sidebar.markdown("**Current session**")
        st.sidebar.code(av.artifact_version, language=None)
        st.sidebar.caption(f"prompt_hash={av.prompt_hash[:12]} · tools_hash={av.tools_hash[:12]}")
        transcript_path = st.session_state.get("transcript_path")
        if transcript_path:
            st.sidebar.caption(f"transcript: {transcript_path.name}")

    return provider_name, version, (model or None), system_prompt_path, tools_path, history_window, max_tool_rounds


def chat_tab(provider_name: str, model: str | None, system_prompt_path: Path, tools_path: Path, history_window: int, max_tool_rounds: int) -> None:
    if st.session_state.get("transcript") is None:
        st.info("Chọn config ở sidebar rồi bấm **Start / reset session** để bắt đầu phiên chat.")
        return

    for turn in st.session_state["display_turns"]:
        render_turn(turn)

    user_text = st.chat_input("Hỏi agent...")
    if not user_text:
        return

    system_prompt = system_prompt_path.read_text(encoding="utf-8")
    tool_declarations = load_tool_declarations(tools_path)
    openai_tools = to_openai_tools(tool_declarations)
    provider = get_provider(provider_name)

    st.session_state["turn_index"] += 1
    messages = [
        {"role": "system", "content": system_prompt},
        *trim_history(st.session_state["history"], history_window),
        {"role": "user", "content": user_text},
    ]

    turn_record: dict[str, Any] = {
        "turn_index": st.session_state["turn_index"],
        "started_at": now_iso(),
        "user": user_text,
        "status": "started",
        "assistant_text": None,
        "rounds": [],
        "tool_events": [],
    }

    with st.spinner("Agent đang xử lý..."):
        try:
            result = run_model_tool_loop(
                provider=provider,
                messages=messages,
                tools=openai_tools,
                model=model,
                max_tool_rounds=max_tool_rounds,
            )
            turn_record.update(result)
            assistant_text = result["assistant_text"]
            st.session_state["history"].append({"role": "user", "content": user_text})
            st.session_state["history"].append({"role": "assistant", "content": assistant_text})
        except Exception as exc:
            turn_record.update({"status": "provider_error", "error": f"{type(exc).__name__}: {str(exc)}"})

    turn_record["ended_at"] = now_iso()
    st.session_state["display_turns"].append(turn_record)
    st.session_state["transcript"]["turns"].append(turn_record)
    write_transcript(st.session_state["transcript_path"], st.session_state["transcript"])
    st.rerun()


def browse_tab() -> None:
    st.subheader("So sánh run / transcript đã lưu (đổi version ở sidebar để chạy lại cùng scenario)")
    col1, col2 = st.columns(2)
    run_files = sorted(RUNS_DIR.glob("*.json")) if RUNS_DIR.exists() else []
    transcript_files = sorted(TRANSCRIPTS_DIR.glob("*.transcript.json")) if TRANSCRIPTS_DIR.exists() else []

    with col1:
        st.markdown("**Run JSON (eval)**")
        picked_run = st.selectbox("Chọn run", ["-"] + [f.name for f in run_files])
        if picked_run != "-":
            data = json.loads((RUNS_DIR / picked_run).read_text(encoding="utf-8"))
            st.caption(f"artifact_version={data.get('artifact_version')} · provider={data.get('provider')}")
            st.json(data.get("summary", {}))
            with st.expander("Full run JSON"):
                st.json(data)

    with col2:
        st.markdown("**Transcript (live chat)**")
        picked_t = st.selectbox("Chọn transcript", ["-"] + [f.name for f in transcript_files])
        if picked_t != "-":
            data = json.loads((TRANSCRIPTS_DIR / picked_t).read_text(encoding="utf-8"))
            st.caption(f"artifact_version={data.get('artifact_version')} · provider={data.get('provider')}")
            for turn in data.get("turns", []):
                st.markdown(f"**Turn {turn.get('turn_index')}** — {turn.get('user')}")
                st.write(turn.get("assistant_text"))
            with st.expander("Full transcript JSON"):
                st.json(data)


def main() -> None:
    init_session()
    st.title("🔎 Research Agent — Demo UI")
    provider_name, _version, model, system_prompt_path, tools_path, history_window, max_tool_rounds = sidebar()

    tab_chat, tab_browse = st.tabs(["💬 Chat", "📊 Runs & Transcripts"])
    with tab_chat:
        chat_tab(provider_name, model, system_prompt_path, tools_path, history_window, max_tool_rounds)
    with tab_browse:
        browse_tab()


if __name__ == "__main__":
    main()

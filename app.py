import json
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from env_loader import load_lab_env
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version
from chat import (
    run_model_tool_loop,
    trim_history,
    write_transcript,
    now_iso,
    safe_slug,
    ROOT,
    ARTIFACTS_DIR,
)

# Nạp môi trường phòng lab
load_lab_env(ROOT)

# Cấu hình giao diện Streamlit
st.set_page_config(
    page_title="Research Agent Lab",
    page_icon="🤖",
    layout="wide",
)

st.title("🤖 Research Agent UI")
st.caption("Giao diện tương tác và theo dõi Tool Call trace của Research Agent")

# Sidebar - Cấu hình Provider, Version và Parameters
with st.sidebar:
    st.header("⚙️ Cấu hình Agent")
    
    provider_name = st.selectbox(
        "Model Provider",
        options=["openrouter", "openai", "anthropic", "gemini"],
        index=0,
    )
    
    version_label = st.text_input("Artifact Version Label", value="v0")
    model_override = st.text_input("Custom Model (Tùy chọn)", value="", help="Để trống nếu muốn dùng model mặc định của provider")
    
    col1, col2 = st.columns(2)
    with col1:
        history_window = st.number_input("History Window", min_value=1, max_value=20, value=5)
    with col2:
        max_tool_rounds = st.number_input("Max Tool Rounds", min_value=1, max_value=10, value=4)
        
    system_prompt_path = ARTIFACTS_DIR / "system_prompt.md"
    tools_path = ARTIFACTS_DIR / "tools.yaml"
    
    # Nạp prompt và tools
    system_prompt = system_prompt_path.read_text(encoding="utf-8") if system_prompt_path.exists() else ""
    tool_declarations = load_tool_declarations(tools_path) if tools_path.exists() else []
    openai_tools = to_openai_tools(tool_declarations) if tool_declarations else []
    
    # Tính artifact version hash
    artifact_version = build_artifact_version(version_label, system_prompt_path, tools_path)
    
    st.divider()
    st.markdown("### 📋 Thống kê Version")
    st.json(artifact_version_dict(artifact_version))
    
    if st.button("🗑️ Xóa lịch sử Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.history = []
        st.session_state.turn_index = 0
        st.session_state.transcript = None
        st.session_state.transcript_path = None
        st.rerun()

# Khởi tạo Session State
if "messages" not in st.session_state:
    st.session_state.messages = []
if "history" not in st.session_state:
    st.session_state.history = []
if "turn_index" not in st.session_state:
    st.session_state.turn_index = 0
if "transcript_path" not in st.session_state or st.session_state.transcript_path is None:
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    transcript_id = "_".join([safe_slug(version_label), safe_slug(provider_name), timestamp])
    transcripts_dir = ROOT / "transcripts"
    st.session_state.transcript_path = transcripts_dir / f"{transcript_id}.transcript.json"
    
    try:
        provider_obj = make_provider(provider_name)
        selected_model = model_override.strip() or getattr(provider_obj, "default_model", None)
    except Exception:
        selected_model = None

    st.session_state.transcript = {
        "transcript_id": transcript_id,
        **artifact_version_dict(artifact_version),
        "provider": provider_name,
        "model": selected_model,
        "system_prompt": str(system_prompt_path),
        "tools": str(tools_path),
        "history_window": history_window,
        "max_tool_rounds": max_tool_rounds,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "turns": [],
    }

# Hiển thị lịch sử chat
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        
        # Nếu có thông tin trace của tools
        if msg.get("rounds"):
            with st.expander("🛠️ Tool Execution Trace", expanded=False):
                for r in msg["rounds"]:
                    st.markdown(f"**Round {r.get('round')}**")
                    if r.get("assistant_text"):
                        st.caption(f"Assistant thoughts: {r.get('assistant_text')}")
                    
                    for call in r.get("tool_calls", []):
                        st.code(f"Tool Call: {call.get('name')}({json.dumps(call.get('args', {}), ensure_ascii=False)})", language="json")
                    
                    for res in r.get("tool_results", []):
                        st.markdown(f"Result for `{res.get('tool')}`:")
                        st.json(res.get("result"))

# Xử lý khi user gửi tin nhắn
if prompt := st.chat_input("Nhập câu hỏi hoặc yêu cầu cho Research Agent..."):
    # Render câu hỏi của user
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Chuẩn bị gọi agent
    st.session_state.turn_index += 1
    messages_payload = [
        {"role": "system", "content": system_prompt},
        *trim_history(st.session_state.history, history_window),
        {"role": "user", "content": prompt},
    ]

    turn_record = {
        "turn_index": st.session_state.turn_index,
        "started_at": now_iso(),
        "user": prompt,
        "status": "started",
        "assistant_text": None,
        "rounds": [],
        "tool_events": [],
    }

    with st.chat_message("assistant"):
        with st.spinner("Agent đang xử lý và gọi tools..."):
            try:
                provider_obj = make_provider(provider_name)
                custom_model = model_override.strip() if model_override.strip() else None

                result = run_model_tool_loop(
                    provider=provider_obj,
                    messages=messages_payload,
                    tools=openai_tools,
                    model=custom_model,
                    max_tool_rounds=max_tool_rounds,
                )
                
                turn_record.update(result)
                assistant_response = result.get("assistant_text", "")
                
                st.markdown(assistant_response)
                
                # Hiển thị tool trace vừa chạy
                if result.get("rounds"):
                    with st.expander("🛠️ Tool Execution Trace", expanded=True):
                        for r in result["rounds"]:
                            st.markdown(f"**Round {r.get('round')}**")
                            if r.get("assistant_text"):
                                st.caption(f"Assistant thoughts: {r.get('assistant_text')}")
                            
                            for call in r.get("tool_calls", []):
                                st.code(f"Tool Call: {call.get('name')}({json.dumps(call.get('args', {}), ensure_ascii=False)})", language="json")
                            
                            for res in r.get("tool_results", []):
                                st.markdown(f"Result for `{res.get('tool')}`:")
                                st.json(res.get("result"))

                # Cập nhật lịch sử chat và session
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": assistant_response,
                    "rounds": result.get("rounds", []),
                })
                st.session_state.history.append({"role": "user", "content": prompt})
                st.session_state.history.append({"role": "assistant", "content": assistant_response})

            except Exception as exc:
                error_msg = f"{type(exc).__name__}: {str(exc)}"
                turn_record.update({
                    "status": "provider_error",
                    "error": error_msg,
                })
                st.error(f"Lỗi Provider: {error_msg}")
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"⚠️ Lỗi: {error_msg}",
                })

            turn_record["ended_at"] = now_iso()
            if st.session_state.transcript:
                st.session_state.transcript["turns"].append(turn_record)
                write_transcript(st.session_state.transcript_path, st.session_state.transcript)

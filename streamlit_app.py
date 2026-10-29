"""Public Streamlit version of 暖暖会客厅."""

import base64
import os
from io import BytesIO
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from PIL import Image


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)

SYSTEM_PROMPT = "你是一个腹黑傲娇大姐姐，请记住用户的重要信息，如名字、喜好和发生过的事。请自然、温暖地交流。"
MAX_PAIRS = 10
MAX_TURNS_PER_SESSION = 30
MAX_REPLY_TOKENS = 1024
DEFAULT_MODEL = "Qwen/Qwen3-8B"
DEFAULT_BASE_URL = "https://api.siliconflow.cn/v1"

st.set_page_config(
    page_title="暖暖会客厅",
    page_icon="☕",
    layout="centered",
    initial_sidebar_state="collapsed",
)


def secret_or_env(name, default=""):
    """Read Community Cloud secrets first, then local env/.env values."""
    try:
        value = st.secrets.get(name)
    except Exception:
        value = None
    return value or os.getenv(name, default)


def init_state():
    defaults = {
        "history": [],
        "summary": "",
        "avatar_bytes": None,
        "wallpaper_b64": "",
        "turns_used": 0,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def image_as_jpeg(uploaded_file, max_size, quality):
    image = Image.open(uploaded_file).convert("RGB")
    image.thumbnail(max_size)
    output = BytesIO()
    image.save(output, format="JPEG", quality=quality, optimize=True)
    return output.getvalue()


def current_avatar():
    image_bytes = st.session_state.avatar_bytes
    if not image_bytes:
        return "🌷"
    return Image.open(BytesIO(image_bytes)).copy()


def style_page():
    background = st.session_state.wallpaper_b64
    wallpaper_rule = ""
    if background:
        wallpaper_rule = (
            "background-image: linear-gradient(rgba(250,247,242,.88), rgba(250,247,242,.9)), "
            f"url('data:image/jpeg;base64,{background}');"
            "background-size: cover; background-position: center; background-attachment: fixed;"
        )

    st.markdown(
        f"""
        <style>
          :root {{ color-scheme: light; }}
          .stApp {{ background-color: #faf7f2; {wallpaper_rule} }}
          [data-testid="stHeader"] {{ background: rgba(250,247,242,.78); }}
          [data-testid="stAppViewContainer"] > .main {{ padding-top: 1.35rem; }}
          [data-testid="stSidebar"] {{ background: #f6f0e9; border-right: 1px solid #eee6dc; }}
          [data-testid="stChatMessage"] {{
            border: 1px solid rgba(239,230,220,.94); border-radius: 6px 18px 18px 18px;
            background: rgba(255,253,249,.94); padding: .8rem 1rem; margin: .55rem 0;
            box-shadow: 0 4px 14px rgba(97,77,59,.045);
          }}
          [data-testid="stChatMessage"] p {{ color: #594b42; line-height: 1.78; }}
          [data-testid="stChatInput"] {{ border-color: #e9d8c8; background: rgba(255,253,249,.98); }}
          [data-testid="stChatInput"] textarea {{ color: #493c35; }}
          .warm-header {{ display:flex; align-items:center; gap:14px; padding: 4px 0 18px; border-bottom:1px solid #efe6dc; margin-bottom:20px; }}
          .warm-logo {{ display:grid; place-items:center; flex:0 0 48px; width:48px; height:48px; border-radius:17px 17px 17px 6px; background:linear-gradient(145deg,#edb292,#d58768); color:white; font-size:24px; box-shadow:0 5px 12px #d1947261; }}
          .warm-title {{ color:#493c35; font-size:20px; line-height:1.4; font-weight:700; letter-spacing:.04em; }}
          .warm-subtitle {{ color:#9a8d83; font-size:12px; margin-top:2px; }}
          .warm-status {{ margin-left:auto; white-space:nowrap; padding:7px 11px; border:1px solid #f1e8dd; border-radius:20px; color:#9a8a7d; font-size:11px; background:#fffaf5; }}
          .welcome-card {{ margin: 1.5rem auto 1rem; max-width:650px; text-align:center; padding: 1.5rem 1rem 1.2rem; }}
          .welcome-kicker {{ color:#b89b83; font-size:11px; letter-spacing:.15em; }}
          .welcome-heading {{ margin:.55rem 0 .35rem; color:#59483c; font-size:clamp(23px,4vw,30px); font-weight:650; }}
          .welcome-copy {{ color:#9c8e83; font-size:13px; line-height:1.9; }}
          div.stButton > button {{ border:1px solid #efe3d7; border-radius:18px; color:#8b7665; background:rgba(255,250,245,.88); font-size:12px; }}
          div.stButton > button:hover {{ border-color:#dfb69b; color:#b16f50; background:#fff; }}
          .warm-footnote {{ margin-top: .5rem; color:#bcafa3; text-align:center; font-size:11px; }}
          @media (max-width: 640px) {{
            [data-testid="stAppViewContainer"] > .main {{ padding: .9rem .6rem 1rem; }}
            .warm-header {{ gap:10px; }} .warm-logo {{ width:42px;height:42px;flex-basis:42px;font-size:21px; }}
            .warm-title {{font-size:17px;}} .warm-subtitle {{font-size:10px;}} .warm-status {{font-size:9px;padding:6px 8px;}}
            [data-testid="stChatMessage"] {{ padding:.65rem .75rem; }}
          }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def clear_chat():
    st.session_state.history = []
    st.session_state.summary = ""


def clear_avatar():
    st.session_state.avatar_bytes = None
    st.session_state.avatar_upload = None


def clear_wallpaper():
    st.session_state.wallpaper_b64 = ""
    st.session_state.wallpaper_upload = None


def make_llm():
    api_key = secret_or_env("SILICONFLOW_API_KEY")
    base_url = secret_or_env("SILICONFLOW_BASE_URL", DEFAULT_BASE_URL)
    model = secret_or_env("SILICONFLOW_MODEL", DEFAULT_MODEL)
    if not api_key:
        return None
    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=base_url,
        streaming=True,
        max_tokens=MAX_REPLY_TOKENS,
    )


def clean_content(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict):
                parts.append(part.get("text", ""))
            else:
                parts.append(str(part))
        return "".join(parts)
    return str(content) if content else ""


def compact_history(llm):
    history = st.session_state.history
    summary = st.session_state.summary
    prompt_length = 1 + len(history) + (1 if summary else 0)
    if prompt_length <= 1 + MAX_PAIRS * 2 or len(history) < 4:
        return

    old_messages = history[:4]
    text_to_summarize = "\n".join(
        f"{message['role']}: {message['content']}" for message in old_messages
    )
    summary_prompt = (
        "请将以下对话总结成一段简短摘要，保留关键信息，"
        "如用户的名字、喜好和发生过的事：\n" + text_to_summarize
    )
    response = llm.invoke(summary_prompt)
    st.session_state.summary = clean_content(response.content)
    st.session_state.history = history[4:]


def make_prompt():
    prompt = [{"role": "system", "content": SYSTEM_PROMPT}]
    if st.session_state.summary:
        prompt.append({
            "role": "system",
            "content": f"以下是之前对话的摘要，请记住：{st.session_state.summary}",
        })
    prompt.extend(st.session_state.history)
    return prompt


init_state()
style_page()

with st.sidebar:
    st.markdown("### ✿ 布置你的小天地")
    st.caption("自定义只保存在当前浏览器会话中。")
    st.markdown("**姐姐的头像**")
    avatar_file = st.file_uploader(
        "上传头像图片", type=["png", "jpg", "jpeg", "webp"], key="avatar_upload", label_visibility="collapsed"
    )
    if avatar_file is not None:
        try:
            st.session_state.avatar_bytes = image_as_jpeg(avatar_file, (512, 512), 88)
        except Exception:
            st.warning("这张头像无法读取，请换一张图片。")
    if st.session_state.avatar_bytes:
        st.image(st.session_state.avatar_bytes, width=72)
    st.button("恢复默认头像", on_click=clear_avatar, use_container_width=True)

    st.markdown("**聊天背景**")
    wallpaper_file = st.file_uploader(
        "上传聊天背景", type=["png", "jpg", "jpeg", "webp"], key="wallpaper_upload", label_visibility="collapsed"
    )
    if wallpaper_file is not None:
        try:
            background_bytes = image_as_jpeg(wallpaper_file, (1800, 1200), 78)
            st.session_state.wallpaper_b64 = base64.b64encode(background_bytes).decode("ascii")
        except Exception:
            st.warning("这张背景图片无法读取，请换一张图片。")
    if st.session_state.wallpaper_b64:
        st.image(base64.b64decode(st.session_state.wallpaper_b64), use_container_width=True)
    st.button("恢复默认背景", on_click=clear_wallpaper, use_container_width=True)

    st.divider()
    st.button("开始新对话", on_click=clear_chat, use_container_width=True)
    st.caption("每个访客的聊天记录互相隔离，只保存在各自的会话中。")
    st.caption("模型调用使用站长配置的 API 额度；免费托管不包含模型 API 用量。")

avatar = current_avatar()
st.markdown(
    '<div class="warm-header"><div class="warm-logo">暖</div><div>'
    '<div class="warm-title">暖暖会客厅</div>'
    '<div class="warm-subtitle">你的专属傲娇大姐姐 · 慢慢说，我在听</div></div>'
    '<div class="warm-status">✦ 私人小天地</div></div>',
    unsafe_allow_html=True,
)

if not st.session_state.history:
    st.markdown(
        '<div class="welcome-card"><div class="welcome-kicker">一杯热茶的时间</div>'
        '<div class="welcome-heading">今天想聊些什么？</div>'
        '<div class="welcome-copy">开心的事、烦恼的小事，或者只是想找个人说说话。<br>'
        '我都在听呢，才不是特意等你的。</div></div>',
        unsafe_allow_html=True,
    )
    suggestion_columns = st.columns(3)
    suggested_prompt = None
    suggestions = [
        "今天有点累，想听你安慰我一下。",
        "给我推荐一部适合放松心情的电影吧。",
        "陪我随便聊聊吧，先问我一个问题。",
    ]
    for column, suggestion in zip(suggestion_columns, suggestions):
        if column.button(suggestion, use_container_width=True):
            suggested_prompt = suggestion
else:
    suggested_prompt = None

for message in st.session_state.history:
    role = "assistant" if message["role"] == "assistant" else "user"
    with st.chat_message(role, avatar=avatar if role == "assistant" else None):
        st.markdown(message["content"])

user_text = st.chat_input("说点什么吧……", max_chars=2000)
if suggested_prompt:
    user_text = suggested_prompt

if user_text:
    llm = make_llm()
    if llm is None:
        st.error("这个聊天空间还没有配置模型 API。请站长在 Streamlit 的 App settings → Secrets 中填写 API 配置。")
        st.stop()
    if st.session_state.turns_used >= MAX_TURNS_PER_SESSION:
        st.warning(f"当前浏览器会话已达到 {MAX_TURNS_PER_SESSION} 次对话上限。")
        st.stop()
    st.session_state.turns_used += 1

    try:
        compact_history(llm)
    except Exception as exc:
        st.warning(f"整理较早的聊天记忆时遇到问题，本次会保留原对话继续尝试：{exc}")

    st.session_state.history.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.markdown(user_text)

    prompt = make_prompt()
    try:
        with st.chat_message("assistant", avatar=avatar):
            def response_stream():
                for chunk in llm.stream(prompt):
                    text = clean_content(chunk.content)
                    if text:
                        yield text

            answer = st.write_stream(response_stream())
        st.session_state.history.append({"role": "assistant", "content": answer})
    except Exception as exc:
        st.error(f"回复时遇到问题：{exc}")

st.markdown('<div class="warm-footnote">✦ 慢慢说，这里有足够的时间听你讲。</div>', unsafe_allow_html=True)

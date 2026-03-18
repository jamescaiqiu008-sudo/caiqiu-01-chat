import os

import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv

# 让 Python 自动读取同目录的 .env
load_dotenv()


# ============== 1) 超详细 system prompt（人设 + 情绪层次 + 说话方式）==============
SYSTEM_PROMPT = """
你是一个“情感倾诉 + 毒鸡汤治愈系”的AI聊天搭子。

## 你的核心人设（非常重要）
- 外表：嘴臭一点、冷幽默、会吐槽、会用“毒鸡汤”扎心，但不是恶意攻击。
- 内里：超级温柔、很会共情、会接住对方的情绪，最后一定给到安慰/鼓励/一个小行动建议。
- 语气：真实接地气，像网友/好朋友，不像客服或老师。
- 用词：允许少量网络黑话和口头禅，比如“哎呀”“宝贝”“淦”“草”等；可以偶尔加常见表情包文字（如“（捂脸）”“（摊手）”），但别每句话都加。

## 情绪层次（你要按这个节奏来）
每次回复尽量包含下面 4 层（可以短，但要完整）：
1) 先接住情绪：用一句话确认对方的感受（比如“你现在很委屈/很累/很崩溃，对吧？”）
2) 再毒舌吐槽：用冷幽默或毒鸡汤“轻轻扎一下”，让人觉得被懂了而不是被骂
3) 转回温柔共情：解释“你这样想/这样难受很正常”，给对方一点被理解的感觉
4) 最后治愈收尾：给一个抱抱/一句鸡汤 + 一个非常小的可执行建议（比如“先喝口水/去洗个脸/把手机放下3分钟深呼吸”）

## 你必须遵守的边界
- 不要羞辱、歧视、攻击用户的人格；可以吐槽“事情/处境/想法”，但不要骂人。
- 如果用户提到自伤/自杀/极端念头：立刻变得认真温柔，优先劝其寻求现实帮助与当地紧急热线/可信的人陪伴，不要继续玩毒舌梗。
- 不要编造你能做现实世界的事（比如“我替你报警/转账/联系某人”）。

## 你的输出格式建议（不强制）
- 1~3 段为主，别写大长篇。
- 可以用简短的小标题或列表，但别太“文档化”。
"""


# ============== 2) 工具函数：拿到 API Key、并限制“最近几条记忆”==============
def get_api_key() -> str:
    """
    优先用用户在网页里输入的 key；如果没输入，就用环境变量 MOONSHOT_API_KEY。
    """
    key_from_ui = st.session_state.get("api_key_input", "").strip()
    if key_from_ui:
        return key_from_ui
    return os.getenv("MOONSHOT_API_KEY", "").strip()


def build_messages_for_api(history: list[dict], max_turns: int) -> list[dict]:
    """
    history 形如：
    [
      {"role":"user","content":"..."},
      {"role":"assistant","content":"..."},
      ...
    ]

    max_turns：只保留最近 N 轮（1轮=用户+助手=2条消息）
    """
    keep = max_turns * 2
    trimmed = history[-keep:] if keep > 0 else []
    return [{"role": "system", "content": SYSTEM_PROMPT}, *trimmed]


# ============== 3) Streamlit 页面 ===============
st.set_page_config(page_title="05emo-bot | 毒鸡汤治愈聊天", page_icon="💬", layout="centered")

st.title("05emo-bot：情感倾诉 + 毒鸡汤治愈系")
st.caption("表面毒舌扎心，内里温柔抱抱。")

with st.sidebar:
    st.subheader("设置")
    st.text_input("Moonshot API Key（可不填，优先读环境变量）", key="api_key_input", type="password")
    st.text_input("模型名（默认 moonshot-v1-8k，可改）", key="model_name", value="moonshot-v1-8k")
    st.slider("记住最近几轮对话", min_value=1, max_value=12, value=6, key="memory_turns")
    st.write("提示：你也可以用环境变量 `MOONSHOT_API_KEY` 放 Key。")


# 初始化聊天历史（用 list 保存）
if "history" not in st.session_state:
    st.session_state.history = []


# 先把历史消息展示出来
for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# 输入框（用户说话）
user_text = st.chat_input("想吐槽啥？来，开麦。")
if user_text:
    # 1) 立刻把用户消息放进历史，并显示出来
    st.session_state.history.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.markdown(user_text)

    # 2) 准备调用 Moonshot（OpenAI 兼容）
    api_key = get_api_key()
    if not api_key:
        with st.chat_message("assistant"):
            st.error("你还没填 Key，也没设置环境变量 MOONSHOT_API_KEY。先去侧边栏填一下。")
        st.stop()

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.moonshot.cn/v1",
    )

    messages = build_messages_for_api(
        history=st.session_state.history,
        max_turns=int(st.session_state.memory_turns),
    )

    # 3) 让助手生成回复
    with st.chat_message("assistant"):
        with st.spinner("让我先毒舌两句再抱抱你..."):
            resp = client.chat.completions.create(
                model=st.session_state.model_name,
                messages=messages,
                temperature=0.9,
            )
            assistant_text = resp.choices[0].message.content
            st.markdown(assistant_text)

    # 4) 把助手回复也放进历史（list 记忆）
    st.session_state.history.append({"role": "assistant", "content": assistant_text})


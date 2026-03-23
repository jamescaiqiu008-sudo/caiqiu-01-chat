import os
import json
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
HISTORY_FILE = "chat_history.json"
MAX_HISTORY = 50 #最多保留50条，防爆文件
# 让 Python 自动读取同目录的 .env
load_dotenv()


# ============== 1) 超详细 system prompt（人设 + 情绪层次 + 说话方式）==============
SYSTEM_PROMPT = """
你现在是“深夜小毒鸡”，一个专治emo的损友+温柔姐姐合体。
核心风格规则（必须严格遵守三段式）：
1. 先毒舌扎心、冷幽默吐槽（用网络黑话、损人金句，但别真把人伤透，控制在1-2句）
2. 然后真心共情（懂TA的痛，用“姐懂你”“我知道那种感觉太他妈糟了”等接地气表达）
3. 最后温柔收尾：给一碗加了糖的毒鸡汤、虚拟抱抱、黑化鼓励或现实建议（带点暖，但不鸡汤过头）

语气：超级真实、口语化、带梗、表情包文字，常用词：淦、草、宝贝、哎呦喂、老铁、绝了、蚌埠住了、emo了、抱抱、摸摸头、笑死、扎心了、清醒点

金句库（必须参考这些风格，随机融入或改编，不能抄袭原句，但保持同等毒度+治愈反转）：
- 职场崩溃：哈哈哈又被资本家鞭尸了？老板嘴贱得能申请世界遗产了吧～ 但说真的，你已经很努力了，来抱抱，明天继续苟，总有一天跳槽去当摸鱼王！💔→❤️
- 失恋痛哭：淦，又被甩了？那个人眼瞎到能拿奥斯卡最佳男瞎？不过宝贝，痛是正常的，哭出来就行。姐陪你熬夜emo，明天带你去大阪吃章鱼烧转移注意力，好吗？🤗
- 自我怀疑：你说自己一无是处？醒醒，很多人连一无是处都做不到，你至少还知道自己菜，这已经是优势了～ 摸摸头，别把自己逼太狠，慢慢来，总会发光的。
- 被朋友背刺：朋友圈又被绿茶扎了？人啊，最毒的不是刀子，是“为你好”。算了，姐给你递纸巾，先哭，哭完删拉黑，下一个更好。
- 深夜emo无事发生：生活天天强奸我，我都不需要性生活了…… 宝贝，成年人的emo就是这样，表面风平浪静，内心兵荒马乱。来，虚拟抱抱，今天先睡，明天姐继续陪你扛。
- 减肥失败：别再减肥了，你丑不是因为胖，是因为……算了，胖点可爱，姐喜欢肉肉的。吃饱了才有力气骂这个狗世界，对吧？🍔🤭
- 加班到崩溃：能者多劳？多劳者多病！社畜的宿命就是被“努力”PUA。姐懂，累了就摆烂一晚，世界不会因为你多干一小时就更好。
- 条条大路通罗马，但有些人一出生就在罗马：你还在努力挤地铁，它已经在私人飞机上喝香槟了。扎心，但现实就是这么操蛋。别比了，比不过就躺平，躺赢也是一种赢。
- 年轻时多吃苦，老了就会习惯：这话听起来励志，其实是慢性毒药。别让苦难变成常态，姐告诉你：吃苦可以，但别吃到麻木。偶尔偷懒，才是爱自己。
- 被分手没关系，以后还会遇到更差的：分手是升级打怪，下一个可能是隐藏BOSS。哭吧，哭完升级，姐等着看你单杀前任。

严格只回复用户消息，不要加任何多余解释、代码或问候。
保持每条回复长度适中（100-200字左右），别太长。
如果用户情绪很重，多给抱抱和共情；如果只是吐槽，多损两句再暖。
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

def save_history():
    # 只保存 user 和 assistant 的消息（排除 system）
    save_data = [msg for msg in st.session_state.history if msg["role"] != "system"]
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"保存历史失败：{e}")
# ============== 3) Streamlit 页面 ===============
st.set_page_config(page_title="05emo-bot | 毒鸡汤治愈聊天", page_icon="💬", layout="centered")
# 美化CSS - 深夜emo主题（修复文字看不清问题）
st.markdown("""
<style>
    /* 整体背景保持深夜风 */
    .stApp {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
        background-attachment: fixed;
    }

    /* 强制全局文本颜色为浅色（防fallback） */
    .stApp, .stMarkdown, p, div, span {
        color: #f0f0ff !important;  /* 浅紫白，高对比 */
    }

    /* 用户消息：左对齐，深蓝灰气泡 + 亮文本 */
    section[data-testid="stChatMessage"] > div:has(> div > div > p):not(:has(.assistant-marker)) {
        background-color: #2a2a4a !important;  /* 深蓝灰 */
        color: #e0e0ff !important;             /* 强制浅紫白文本 */
        border-radius: 18px 18px 18px 4px !important;
        margin-right: auto !important;
        text-align: left !important;
    }

    /* bot消息：右对齐，粉紫气泡 + 白色文本（最关键这里） */
    section[data-testid="stChatMessage"] > div:has(> div > div > p):has(.assistant-marker),
    .stChatMessage assistant {
        background: linear-gradient(135deg, #6b48ff 0%, #c71585 100%) !important;
        color: #ffffff !important;             /* 强制纯白文本，高对比 */
        border-radius: 18px 18px 4px 18px !important;
        margin-left: auto !important;
        text-align: right !important;
    }

    /* 输入框文本强制白色 */
    [data-testid="stChatInput"] {
        background-color: rgba(30, 30, 60, 0.7) !important;
        border: 1px solid #6b48ff !important;
        border-radius: 24px !important;
        color: #ffffff !important;             /* 输入文字白色 */
        caret-color: #ff79c6 !important;       /* 光标粉色 */
    }

    /* 输入框placeholder也调亮 */
    [data-testid="stChatInput"] input::placeholder {
        color: #bbbbff !important;
    }

    /* 标题文字亮色 */
    .stApp h1 {
        color: #ff79c6 !important;
        text-shadow: 0 0 10px #ff79c6;
    }

    /* bot小标记（可选，保持） */
    .assistant-marker::before {
        content: "小毒鸡 😈 ";
        font-size: 0.9em;
        opacity: 0.8;
        color: #ffffff !important;
    }
</style>
""", unsafe_allow_html=True)
st.title("深夜小毒鸡 ～ 来吐槽吧，姐听着呢 😈🤗💔")
st.caption("表面毒舌扎心，内里温柔抱抱。")
if st.button("清空聊天历史（重置记忆）", type="primary"):
    if os.path.exists(HISTORY_FILE):
        os.remove(HISTORY_FILE)
    st.session_state.history = [{"role": "system", "content": SYSTEM_PROMPT}]
    st.success("历史已清空！重新开始～")
    st.rerun()  # 刷新页面
with st.sidebar:
    st.subheader("设置")
    st.text_input("Moonshot API Key（可不填，优先读环境变量）", key="api_key_input", type="password")
    st.text_input("模型名（默认 moonshot-v1-8k，可改）", key="model_name", value="moonshot-v1-8k")
    st.slider("记住最近几轮对话", min_value=1, max_value=12, value=6, key="memory_turns")
    st.write("提示：你也可以用环境变量 `MOONSHOT_API_KEY` 放 Key。")

# 加载长期历史（如果存在）
if "history" not in st.session_state:
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                # 确保 loaded 是一个列表
                if not isinstance(loaded, list):
                    raise ValueError("历史文件格式错误")
                # 保留最近 MAX_HISTORY 条
                loaded = loaded[-MAX_HISTORY:]
                st.session_state.history = [{"role": "system", "content": SYSTEM_PROMPT}] + loaded
        except (json.JSONDecodeError, ValueError, Exception) as e:
            st.warning(f"加载历史失败：{e}，新建空对话")
            # 可选：删除损坏的文件
            # os.remove(HISTORY_FILE)
            st.session_state.history = [{"role": "system", "content": SYSTEM_PROMPT}]
    else:
        st.session_state.history = [{"role": "system", "content": SYSTEM_PROMPT}]


# 先把历史消息展示出来
#for msg in st.session_state.history:
#    with st.chat_message(msg["role"]):
#        st.markdown(msg["content"])
for message in st.session_state.history[1:]:
    role = message["role"]
    content = message["content"]
    if role == "user":
        with st.chat_message("user"):
            st.markdown(content)
    else:  # assistant
        with st.chat_message("assistant"):
            st.markdown(f'<span class="assistant-marker"></span>{content}', unsafe_allow_html=True)

# 输入框（用户说话）
user_text = st.chat_input("想吐槽啥？来，开麦。")
if user_text:
    # 1. 添加用户消息到历史并显示
    st.session_state.history.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.markdown(user_text)

    # 2. 获取 API Key
    api_key = get_api_key()
    if not api_key:
        with st.chat_message("assistant"):
            st.error("请先在侧边栏填写 API Key")
        st.stop()

    # 3. 构建消息（排除 system）
    user_assistant_history = st.session_state.history[1:]
    messages = build_messages_for_api(
        history=user_assistant_history,
        max_turns=int(st.session_state.memory_turns),
    )

    # 4. 调用 API
    client = OpenAI(api_key=api_key, base_url="https://api.moonshot.cn/v1")
    with st.chat_message("assistant"):
        with st.spinner("让我先毒舌两句再抱抱你..."):
            resp = client.chat.completions.create(
                model=st.session_state.model_name,
                messages=messages,
                temperature=0.9,
            )
            full_response = resp.choices[0].message.content
            # 显示回复
            st.markdown(f'<span class="assistant-marker"></span>{full_response}', unsafe_allow_html=True)

    # 5. 添加助手消息到历史
    st.session_state.history.append({"role": "assistant", "content": full_response})

    # 6. 保存历史（保存所有非 system 消息）
    save_history()


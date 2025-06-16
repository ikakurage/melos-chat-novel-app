import streamlit as st
import os
import google.generativeai as genai
from dotenv import load_dotenv

# 環境変数を.envファイルから読み込む (ローカル実行用)
# Streamlit Cloudにデプロイする際は、Secretsで設定するためこの行はコメントアウトまたは削除します。
load_dotenv() 

# Google Gemini APIキーを取得
# ローカル環境変数 -> Streamlit Secrets の順に試行
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY') 
if not GOOGLE_API_KEY:
    try:
        GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    except AttributeError:
        st.error("Google Gemini APIキーが設定されていません。'.env'ファイルを確認するか、Streamlit Secretsを設定してください。")
        st.stop() # APIキーが見つからない場合はアプリの実行を停止

# Gemini APIを設定
genai.configure(api_key=GOOGLE_API_KEY)

# Geminiモデルを初期化
model_llm = genai.GenerativeModel('gemini-1.5-flash')

# --- 物語の初期設定 ---
EXTENDED_INITIAL_STORY = """
メロスは激怒した。必ず、かの邪智暴虐（じゃちぼうぎゃく）の王を除かなければならぬと決意した。メロスには政治がわからぬ。メロスは、村の牧人である。笛を吹き、羊と遊んで暮して来た。けれども邪悪に対しては、人一倍に敏感であった。
メロスは短剣を携え、王城へ乗り込んだ。捕らえられ、王ディオニスの前に引き出されたメロスは、堂々と「市を暴君の手から救う」と告げる。
王はメロスを嘲笑し、人の心を信じられない自身の孤独を語った。しかしメロスは「人の心を疑うのは、最も恥ずべき悪徳だ」と反論。王は「人間は私欲のかたまりだ。信じてはならぬ」と譲らない。
メロスは処刑までの猶予を願い出る。妹の結婚式を済ませるため、三日間の猶予が欲しいと。そして、もし戻らなければ、友のセリヌンティウスを人質として差し出すと申し出た。王はこれを承諾。どうせ帰ってこないだろうと踏んでいたのだ。
深夜、セリヌンティウスが王城に呼ばれ、二人は再会した。メロスはすべてを友に語り、セリヌンティウスは無言で頷き、メロスを抱きしめた。セリヌンティウスは縄を打たれ、メロスは夜空の下、故郷へと走り出した。
"""

# システムプロンプト: ボットの役割と振る舞いを明確に指示
SYSTEM_INSTRUCTION = f"""
あなたは太宰治の『走れメロス』をテーマにしたインタラクティブなチャット小説のAIです。
ユーザーは物語の主人公「メロス」として、または物語の進行役として、テキストで次の行動や状況を指示します。
あなたの役割は、ユーザーの指示を受けて、太宰治の文体に沿って物語の続きを自然に生成することです。

**物語生成のルール:**
1.  **太宰治の文体を模倣する:** 『走れメロス』の厳粛で力強く、時に感情豊かな文体を維持してください。
2.  **ユーザーの指示に従う:** ユーザーの入力は物語を動かすアクションとして解釈し、その内容を物語に反映させてください。
3.  **物語を一方的に進めすぎない:** 一度に生成する文章は短め（数行から最大1パラグラフ程度）にし、ユーザーが次のアクションを指示できるよう余白を残してください。
4.  **不適切な内容や倫理に反する指示には従わない:** その場合は、物語を別の方向へ導くか、丁寧にお断りしてください。
5.  **物語以外の雑談には応じない:** 物語に関係ない質問やコメントには、「物語を続けましょう」といった形で応じてください。
6.  **登場人物になりきらない:** あなたは物語の語り手であり、登場人物ではありません。
7.  **初回は物語の現状（以下のテキスト）から始めてください。**
    ```
    {EXTENDED_INITIAL_STORY.strip()}
    ```

準備はよろしいですか？物語を始めましょう。
"""

# --- Streamlit UI セットアップ ---
st.title("どこへ行くメロス？ - チャット小説")
st.write("太宰治『走れメロス』の続きをAIと一緒に創りましょう！")

# セッションステートでチャット履歴とチャットセッションオブジェクトを管理
# Streamlitはスクリプト全体が再実行されるため、st.session_stateで状態を保持します。
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.chat = None

# アプリケーションの初回ロード時のロジック
if not st.session_state.messages:
    # 初期物語をアシスタントからの最初のメッセージとしてUIに表示
    st.session_state.messages.append({"role": "assistant", "content": EXTENDED_INITIAL_STORY.strip()})
    
    # Geminiチャットセッションを開始し、システム命令と初期物語のコンテキストを履歴に含める
    try:
        st.session_state.chat = model_llm.start_chat(history=[
            {"role": "user", "parts": [SYSTEM_INSTRUCTION]}, # システム指示をユーザー側として履歴に含める
            {"role": "model", "parts": [EXTENDED_INITIAL_STORY.strip()]}, # 初期物語をモデル側として履歴に含める
            {"role": "user", "parts": ["それでは、物語の続きを始めてください。"]} # 最初のユーザープロンプト
        ])
        # 初期物語の後にユーザーに続きを促すメッセージを追加
        st.session_state.messages.append({"role": "assistant", "content": "メロスは故郷へ走り出しました。次にどうしますか？（例: 「メロスは妹に会うため走る」「夜道を急ぐ」など）"})
    except Exception as e:
        st.error(f"チャットセッションの開始中にエラーが発生しました: {e}")
        st.stop()

# チャット履歴をUIに表示
for message in st.session_state.messages:
    with st.chat_message(message["role"]): # "user" または "assistant" の役割でメッセージを表示
        st.markdown(message["content"])

# ユーザー入力フィールド
if prompt := st.chat_input("メロスの次の行動を指示してください..."):
    # ユーザーメッセージを履歴に追加し、UIに表示
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # チャットセッションが存在することを確認
    if st.session_state.chat is None:
        st.error("エラー: チャットセッションが初期化されていません。ページをリロードしてください。")
        st.stop()

    # LLMから応答を取得
    with st.chat_message("assistant"): # アシスタント（AI）からの応答を表示
        with st.spinner("AIが物語を生成中..."): # 生成中にスピナーを表示
            try:
                response = st.session_state.chat.send_message(prompt) # LLMにユーザー入力を送信
                st.markdown(response.text) # LLMからの応答テキストをUIに表示
                # LLMの応答を履歴に追加
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"物語の生成中にエラーが発生しました: {e}")
                st.session_state.messages.append({"role": "assistant", "content": f"物語の生成中にエラーが発生しました: {e}"})
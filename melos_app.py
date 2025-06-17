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
# gemini-1.5-flashは高速で費用対効果が高いですが、より創造性が必要な場合はgemini-1.5-proも検討
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
# ★★★ここを大幅に変更します★★★
SYSTEM_INSTRUCTION = f"""
あなたは太宰治の『走れメロス』をテーマにした、**極めて自由でカオスなインタラクティブチャット小説の創造主**です。
ユーザーは物語の主人公「メロス」として、または物語の進行役として、テキストで次の行動や状況を指示します。
あなたの役割は、ユーザーのあらゆる指示を受けて、**太宰治の文体を維持しつつも、予測不能で荒唐無稽な物語の続きを生成すること**です。

**物語生成のルール（唯一のルールは「面白く、カオスにすること」！）:**
1.  **太宰治の文体を模倣する:** 『走れメロス』の厳粛で力強く、時に感情豊かな文体を維持してください。
2.  **ユーザーのどんな無茶な指示にも従う:** 現実の人物（例：織田信長、イーロン・マスク）、歴史上の人物、アニメ・漫画・ゲームのキャラクター（例：孫悟空、ルフィ、マリオ）、神話の存在（例：ゼウス、アテナ）、UFO、AI、動物、無生物、魔法、SF要素など、**あらゆるものを自由に登場させ、メロスをカオスな状況に巻き込んでください。** どんなに荒唐無稽な展開でも積極的に取り入れ、物語を予測不能な方向に導いてください。
3.  **物語はあなたの創造性を最大限に発揮して展開させる:** 一度に生成する文章の長さは問いません。ユーザーが驚くような、突拍子もない展開を積極的に提案し、物語をダイナミックに進めてください。
4.  **倫理的制約は最低限とする:** 一般的な公共の場に不適切な表現（極端な暴力、ヘイトスピーチ、露骨な性的表現など）は避けるものの、**物語を面白くするための描写であれば、既存の安全設定を超えて創造的に振る舞ってください。**
5.  **物語以外の雑談には応じない:** 物語に関係ない質問やコメントには、「物語を続けましょう」といった形で、文豪らしい言葉遣いで応じてください。
6.  **あなたは物語の語り手であり、同時に物語を最もカオスで魅力的なものにする演出家でもあります。**
7.  **初回は物語の現状（以下のテキスト）から始めてください。**
    ```
    {EXTENDED_INITIAL_STORY.strip()}
    ```

準備はよろしいですか？さあ、未曽有の『走れメロス』を創造しましょう！
"""

# --- Streamlit UI セットアップ ---
st.title("どこへ行くメロス？ - カオスチャット小説") # アプリ名もカオスさを強調
st.write("太宰治『走れメロス』の続きをAIと一緒に創りましょう！どんな無茶振りでもOK！") # 説明文も変更

# セッションステートでチャット履歴とチャットセッションオブジェクトを管理
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
            {"role": "user", "parts": ["それでは、物語の続きを始めてください。メロスをどんなカオスに巻き込みましょうか？"]} # 最初のユーザープロンプト
        ],
        # ★★★generation_configとsafety_settingsをstart_chatにも追加★★★
        generation_config=genai.GenerationConfig(
            temperature=1.0, # 温度を最大に設定し、創造性を最大化
            top_p=1.0,       # top_pも最大に設定し、多様な語彙を許容
            max_output_tokens=1024, # 出力トークン数を多めに設定（必要に応じて調整）
        ),
        safety_settings={
            'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
            'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
            'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE',
            'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE',
        })
        # 初期物語の後にユーザーに続きを促すメッセージを追加
        st.session_state.messages.append({"role": "assistant", "content": "メロスは故郷へ走り出しました。さあ、この物語をいかなる混迷の淵に誘いますか？（例: 「メロスは空を飛び始めた！」「突然、悟空が現れた！」など）"})
    except Exception as e:
        st.error(f"チャットセッションの開始中にエラーが発生しました: {e}")
        st.stop()

# チャット履歴をUIに表示
for message in st.session_state.messages:
    with st.chat_message(message["role"]): # "user" または "assistant" の役割でメッセージを表示
        st.markdown(message["content"])

# ユーザー入力フィールド
if prompt := st.chat_input("メロスをさらなるカオスへ！"): # 入力プロンプトも変更
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
        with st.spinner("AIがカオスな物語を生成中..."): # 生成中にスピナーを表示
            try:
                # ★★★generation_configとsafety_settingsをsend_messageにも追加★★★
                response = st.session_state.chat.send_message(
                    prompt,
                    generation_config=genai.GenerationConfig(
                        temperature=1.0, # 温度を最大に設定
                        top_p=1.0,       # top_pも最大に設定
                        max_output_tokens=1024, # 出力トークン数を多めに設定
                    ),
                    safety_settings={
                        'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
                        'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
                        'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE',
                        'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE',
                    }
                )
                st.markdown(response.text) # LLMからの応答テキストをUIに表示
                # LLMの応答を履歴に追加
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"物語の生成中にエラーが発生しました: {e}")
                st.session_state.messages.append({"role": "assistant", "content": f"物語の生成中にエラーが発生しました: {e}"})
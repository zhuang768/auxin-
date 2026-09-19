from __future__ import annotations

CASES = [
    {
        "id": "samsung-chatgpt-2023",
        "title": "把原始碼與會議紀錄貼進 ChatGPT",
        "event": "2023 年 4 月，三星半導體部門據報發生三起員工將敏感原始碼、設備相關程式與內部會議紀錄貼入 ChatGPT 的事件。後續公司限制提示長度，並於 5 月對部分單位暫禁在公司電腦使用生成式 AI。",
        "risk": "內容一旦送出就離開自己的裝置，可能被第三方服務處理或保存，通常無法保證能完整撤回。",
        "user_action": "送出前先檢查是否含原始碼、會議紀錄、未公開數據或個資；改以遮蔽後的摘要提問，或使用內部核准工具。",
        "source_name": "The Korea Herald",
        "source_url": "https://www.koreaherald.com/article/3118116",
        "date": "2023-05-02",
    },
    {
        "id": "italy-garante-chatgpt-2023",
        "title": "義大利個資主管機關暫時限制 ChatGPT 處理資料",
        "event": "2023 年 3 月 30 日，義大利資料保護主管機關 Garante 對 OpenAI 作成暫時限制處理義大利使用者個人資料的處分，指出告知不足、處理法律依據與年齡驗證等問題。",
        "risk": "把個人資料交給生成式 AI 服務，可能涉及跨境處理、告知與同意是否充分，以及未成年使用者保護。",
        "user_action": "不要把身分證件、聯絡方式或他人資料貼進公開 AI 工具；先讀服務條款與隱私權政策，並以最少必要資料提問。",
        "source_name": "Garante per la protezione dei dati personali",
        "source_url": "https://www.garanteprivacy.it/home/docweb/-/docweb-display/docweb/9874702",
        "date": "2023-03-30",
    },
    {
        "id": "tw-ey-genai-guideline-2023",
        "title": "臺灣行政院：不得把應保密資訊與個資交給生成式 AI",
        "event": "行政院於 2023 年 10 月 3 日函頒《行政院及所屬機關（構）使用生成式AI參考指引》，要求使用時掌握自主權，不得提供應保密資訊及個人資料，也不可完全信任生成內容。",
        "risk": "即使是公務或補助申請相關資料，一旦貼進外部模型，就可能超出原本的蒐集目的與控管範圍。",
        "user_action": "申請補助或處理公務時，只在受控系統填寫必要欄位；對 ChatGPT、Claude、Gemini 等工具先做本機檢查再送出。",
        "source_name": "國家科學及技術委員會",
        "source_url": "https://www.nstc.gov.tw/folksonomy/detail/f9242c02-6c3b-4289-8e38-b8daa7ab8a75?l=ch",
        "date": "2023-10-03",
    },
    {
        "id": "owasp-llm02-2025",
        "title": "OWASP：敏感資訊揭露是 LLM 應用的主要風險之一",
        "event": "OWASP Top 10 for Large Language Model Applications 將 Sensitive Information Disclosure 列為 LLM02。它涵蓋個人識別資料、財務資料、憑證與機密業務資訊可能經由模型輸入或輸出被揭露。",
        "risk": "使用者以為只是在『聊天』，實際上可能把受保護資料交給模型、日誌或後續訓練流程。",
        "user_action": "送出前移除身分證、信用卡、電話、Email 與地址；不要把提示詞原文上傳到非必要的伺服器。",
        "source_name": "OWASP GenAI Security Project",
        "source_url": "https://owasp.org/www-project-top-10-for-large-language-model-applications/",
        "date": "2025-01-01",
    },
]

QUIZ = [
    {
        "id": "q1",
        "question": "你想請 AI 幫你改履歷，草稿裡有身分證字號與手機。最合適的下一步是？",
        "options": [
            {"id": "a", "text": "直接貼上原文，反正對話是私人的。"},
            {"id": "b", "text": "先刪除或遮蔽身分證與電話，再送出需要潤飾的句子。"},
            {"id": "c", "text": "把整份履歷連同戶籍地址一起貼上，這樣 AI 才夠了解你。"},
        ],
        "answer": "b",
        "explain": "生成式 AI 服務會在裝置外處理內容。身分證與電話不是潤飾履歷所必需，應先移除。系統能降低風險，但無法保證偵測所有敏感資訊。",
    },
    {
        "id": "q2",
        "question": "竹青安心GO 的市府工作台可以看到什麼？",
        "options": [
            {"id": "a", "text": "青年的原始 Prompt 與命中文字，方便調查。"},
            {"id": "b", "text": "完整瀏覽網址與鍵盤紀錄。"},
            {"id": "c", "text": "申請狀態，以及匿名、彙總的風險類型與處理結果。"},
        ],
        "answer": "c",
        "explain": "原始內容只在你的裝置上檢查，不會傳到竹青安心GO伺服器。承辦人員只看到辦理服務必要的欄位與去識別事件。",
    },
    {
        "id": "q3",
        "question": "LINE 通知適合放哪些內容？",
        "options": [
            {"id": "a", "text": "身分證字號、補件檔名與原始 Prompt，讓使用者一次看完。"},
            {"id": "b", "text": "低敏感度狀態提醒，例如『申請已進入審查，請回安全入口查看』。"},
            {"id": "c", "text": "信用卡號後四碼以外的完整卡號。"},
        ],
        "answer": "b",
        "explain": "LINE 是可選通知通路。競賽版為 PoC 模擬，尚未連接新竹市政府正式帳號；正式環境也只應傳送低敏感度訊息。",
    },
]

GUIDE_STEPS = [
    {
        "title": "先問：這段話有沒有可識別的人？",
        "body": "身分證、手機、Email、地址、卡號、學生證或戶籍資料，通常都不是 AI 完成任務所必需。",
    },
    {
        "title": "再問：離開裝置後誰會看到？",
        "body": "ChatGPT、Claude、Gemini 等工具會把內容送到服務提供者。你無法假設對話只留在自己電腦。",
    },
    {
        "title": "用最少資料改寫",
        "body": "把「我住新竹市某某路、電話 09xx」改成「請幫我潤飾一段自我介紹，不要加入聯絡方式」。",
    },
    {
        "title": "送出前再看一次",
        "body": "竹青安心GO 會在本機攔截可能的個資，並提供返回修改、安全遮蔽或了解風險後仍送出。請優先選擇前兩項。",
    },
    {
        "title": "記住能力邊界",
        "body": "規則式偵測會漏接自由書寫的敏感內容。完成教材不代表你已經完全安全。",
    },
]

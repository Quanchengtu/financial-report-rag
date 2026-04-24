from bs4 import BeautifulSoup  # 用於解析HTML
import re  #  判斷某些文字是不是 XBRL 雜訊 ＆ 清理多餘空白、換行


def is_probable_xbrl_line(line: str) -> bool:
    """
    判斷這一行是否像 XBRL / iXBRL 的雜訊，而不是正文 return true/false
    """
    lower_line = line.lower() # 統一先轉小寫 方便判斷

    # 常見 namespace / taxonomy / url 雜訊
    if (
        lower_line.startswith("http://")
        or lower_line.startswith("https://")
        or "xbrl" in lower_line
        or "xml" in lower_line
        or "xmlns" in lower_line
        or "us-gaap:" in lower_line
        or "dei:" in lower_line
        or "iso4217:" in lower_line
        or "srt:" in lower_line
    ):
        return True

    # 泛用：像 companyPrefix:TagName 這類 namespace 格式
    if re.match(r"^[a-zA-Z0-9_-]+:[a-zA-Z0-9_-]+$", line):
        return True

    return False


def extract_text_from_html(html: str) -> str:
    """
    將 SEC filing HTML 清洗成較乾淨的純文字
    """

    soup = BeautifulSoup(html, "html.parser")

    # 移除完全不需要的標籤
    for tag in soup(["script", "style", "noscript", "ix:header", "header"]):
        tag.decompose()

    # 移除常見 Inline XBRL / XBRL 標籤
    xbrl_prefixes = (
        "ix:",
        "ixt:",
        "xbrli:",
        "xbrldi:",
        "xlink:",
        "link:",
        "dei:",
        "us-gaap:",
        "srt:",
        "iso4217:",
        "ecd:",
        "country:",
        "currency:",
    )

    for tag in soup.find_all():
        tag_name = tag.name.lower() if tag.name else ""

        if any(tag_name.startswith(prefix) for prefix in xbrl_prefixes):
            tag.decompose()

    target = soup.body if soup.body else soup   # HTML 中有<body>就抓body裡的內容
    text = target.get_text(separator="\n")

    cleaned_lines = []
    for line in text.splitlines():  # 將文字拆成一行一行
        line = line.strip()         # 清除前後空白

        if not line:                # 若該行為空 跳過
            continue

        if is_probable_xbrl_line(line): # 該行像XBRL 雜訊 跳過

            continue

        cleaned_lines.append(line)

    text = "\n".join(cleaned_lines)

    # 將單一換行也適度轉成空格，避免句子被切得太碎
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)
    
    # 壓縮多餘空白
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)

    return text.strip()
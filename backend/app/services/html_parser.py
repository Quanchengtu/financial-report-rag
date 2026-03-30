from bs4 import BeautifulSoup
import re


def extract_text_from_html(html: str) -> str:
    """
    將 SEC filing HTML 清洗成較乾淨的純文字
    目標：
    1. 移除 script / style / noscript
    2. 移除常見 XBRL / iXBRL 雜訊標籤
    3. 保留較可讀的正文文字
    4. 壓縮多餘空白與空行
    """

    soup = BeautifulSoup(html, "html.parser")

    # 1. 移除完全不需要的標籤
    for tag in soup(["script", "style", "noscript", "ix:header", "header"]):
        tag.decompose()

    # 2. 移除常見 Inline XBRL / XBRL 標籤
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

    # 3. 優先抓 body，沒有 body 再退回整份文件
    target = soup.body if soup.body else soup

    text = target.get_text(separator="\n")

    # 4. 清掉常見 XBRL 垃圾字串行
    cleaned_lines = []
    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue

        # 過濾明顯像 XBRL namespace / tag 名稱 / 純代碼的行
        if (
            line.startswith("http://")
            or line.startswith("https://")
            or "xbrl" in line.lower()
            or "us-gaap:" in line.lower()
            or "dei:" in line.lower()
            or "iso4217:" in line.lower()
            or line.lower().startswith("aapl:")
        ):
            continue

        cleaned_lines.append(line)

    text = "\n".join(cleaned_lines)

    # 5. 壓縮空白
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)

    return text.strip()
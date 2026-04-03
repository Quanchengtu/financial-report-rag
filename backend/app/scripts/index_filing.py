# 之後一定需要一個「先建索引」的腳本，不然每次 query 都重新抓 SEC 會很慢。
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.indexing_service import index_filing


def main():
    """
    使用方式：
    python scripts/index_filing.py 1045810 0001045810-24-000029 nvda-20240128.htm NVDA 10-K 2024-02-21
    """
    if len(sys.argv) < 4:
        print("Usage: python scripts/index_filing.py <cik> <accession_number> <primary_document> [ticker] [form_type] [filing_date]")
        return

    cik = sys.argv[1]
    accession_number = sys.argv[2]
    primary_document = sys.argv[3]
    ticker = sys.argv[4] if len(sys.argv) > 4 else None
    form_type = sys.argv[5] if len(sys.argv) > 5 else None
    filing_date = sys.argv[6] if len(sys.argv) > 6 else None

    result = index_filing(
        cik=cik,
        accession_number=accession_number,
        primary_document=primary_document,
        company_ticker=ticker,
        form_type=form_type,
        filing_date=filing_date
    )
    print(result)


if __name__ == "__main__":
    main()
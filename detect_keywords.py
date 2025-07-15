import re
import pandas as pd

class KeywordDetector:
    def __init__(self, excel_path):
        # 엑셀에서 주요단어와 조합키워드 리스트 읽어오기
        df = pd.read_excel(excel_path)
        self.patterns = []
        for _, row in df.iterrows():
            main = str(row['주요단어']).strip()
            combos = [str(c).strip() for c in row[1:] if pd.notnull(c)]
            for c in combos:
                # main-c combo 단어 경계(\b) 매칭 패턴 생성
                token = f"{main}-{c}"
                # 단어 경계로 앞뒤 띄워쓰기 없이도 정확히 매칭
                pat = re.compile(rf"\b{re.escape(main)}-{re.escape(c)}\b")
                self.patterns.append((token, pat))

    def detect(self, text: str):
        found = set()
        for token, pat in self.patterns:
            if pat.search(text):
                found.add(token)
        return sorted(found)
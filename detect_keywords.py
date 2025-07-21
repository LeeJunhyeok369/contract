import re
import pandas as pd

class KeywordDetector:
    def __init__(self, excel_path):
        df = pd.read_excel(excel_path)
        self.patterns = []
        for _, row in df.iterrows():
            main = str(row['키워드']).strip()
            combos = [str(c).strip() for c in row[1:] if pd.notnull(c)]

            # main 단독 패턴 추가
            pat_main = re.compile(rf"\b{re.escape(main)}\b")
            self.patterns.append((main, pat_main))

            # main-combo 패턴도 추가
            for c in combos:
                token = f"{main}-{c}"
                pat_combo = re.compile(rf"\b{re.escape(main)}-{re.escape(c)}\b")
                self.patterns.append((token, pat_combo))

    def detect(self, text: str):
        found = set()
        for token, pat in self.patterns:
            if pat.search(text):
                found.add(token)
        return sorted(found)

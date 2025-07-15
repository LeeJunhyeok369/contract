import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import streamlit as st
import pytesseract
from PIL import Image
import pdfplumber
import re
from predict import predict
from detect_keywords import KeywordDetector
import json
import pandas as pd
import requests

@st.cache_data
def load_defaulter_data(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    df['체불액(원)'] = df['체불액(원)'].str.replace(',', '').astype(int)
    return df

KEYWORD_EXCEL_PATH = "./불공정 키워드.xlsx"
DEFAULTER_JSON_PATH = "./defaulter_list.json"


df_defaulters = load_defaulter_data(DEFAULTER_JSON_PATH)
detector = KeywordDetector(KEYWORD_EXCEL_PATH)

st.set_page_config(page_title="스마트 계약서 검토 시스템", layout="wide")
st.markdown("""
    <h1 style='text-align:center;color:#222;font-weight:700;'>스마트 계약서 검토 시스템</h1>
    <p style='text-align:center;color:#888;font-size:1.1em;'>AI 기반 계약서 분석으로 안전한 계약을 도와드립니다</p>
    """, unsafe_allow_html=True
)

if "contract_type" not in st.session_state:
    st.session_state["contract_type"] = None

button_css = """
<style>
.choice-card {
    background: #fff;
    border: 1.5px solid #e2e2e2;
    border-radius: 16px;
    padding: 32px 18px 18px 18px;
    margin-bottom: 10px;
    box-shadow: 0 2px 12px #f2f2f2;
    text-align: center;
    transition: border 0.15s, box-shadow 0.15s;
}
.choice-card:hover {
    border: 1.5px solid #eee;
    box-shadow: 0 4px 16px #eee;
}
.choice-btn {
    width: 100%%;
    padding: 22px 0 18px 0;
    margin: 0 auto 6px auto;
    background: #f9f9f9;
    color: #222;
    border: 1.5px solid #eee;
    border-radius: 12px;
    font-size: 1.25em;
    font-weight: 600;
    box-shadow: 0 2px 8px #ececec;
    cursor: pointer;
    transition: border 0.15s, background 0.15s, color 0.15s;
}
.btn-desc {
    margin-top: 14px;
    font-size: 1.05em;
    color: #888;
    text-align: center;
}
</style>
"""
st.markdown(button_css, unsafe_allow_html=True)

if st.session_state["contract_type"] is None:
    st.markdown("#### 계약서 종류를 선택하세요")
    col1, col2 = st.columns(2, gap="large")
    with col1:
        st.markdown(
            """
            <div class="choice-card">
                <h3 class="choice-btn">근로계약서</h3>
                <div class="btn-desc">
                    직장 내 근로 조건, 임금, 근무 시간 등<br>
                    노동자와 사업주 간 계약을 분석합니다.
                </div>
            </div>
            """, unsafe_allow_html=True
        )
        if st.button("근로계약서 선택", key="emp_btn_real", use_container_width=True):
            st.session_state["contract_type"] = "근로계약서"
            st.rerun()
    with col2:
        st.markdown(
            """
            <div class="choice-card">
                <h3 class="choice-btn">부동산계약서</h3>
                <div class="btn-desc">
                    임대차, 매매 등<br>
                    부동산 관련 계약서를 분석합니다.
                </div>
            </div>
            """, unsafe_allow_html=True
        )
        if st.button("부동산계약서 선택", key="re_btn_real", use_container_width=True):
            st.session_state["contract_type"] = "부동산계약서"
            st.rerun()

if st.session_state["contract_type"]:
    contract_type = st.session_state["contract_type"]
    state_key = "emp" if contract_type == "근로계약서" else "re"

    st.markdown(f"### {contract_type} 워크플로우")

    def extract_text_from_file(uploaded):
        fname = uploaded.name.lower()
        if fname.endswith(".pdf"):
            with pdfplumber.open(uploaded) as pdf:
                pages = [p.extract_text() or "" for p in pdf.pages]
            return "\n\n".join(pages)
        elif any(fname.endswith(ext) for ext in ["png","jpg","jpeg"]):
            return pytesseract.image_to_string(Image.open(uploaded), lang="kor+eng")
        else:
            return uploaded.read().decode("utf-8", errors="ignore")

    def analyze_contract(text):
        try:
            cat = predict(text)
        except:
            cat = "분류 실패"
        sents = [s.strip() for s in text.replace("?",".").split(".") if len(s.strip())>20]
        summary = ". ".join(sents[:3]) + ("…" if len(sents)>3 else "")
        try:
            kws = detector.detect(text)
        except:
            kws = []
        clauses = {}
        sents_full = re.split(r'(?<=[\.\?\!])\s+', text)
        if kws:
            for kw in kws:
                matched = [s for s in sents_full if re.search(rf"\b{re.escape(kw)}\b", s)]
                if matched:
                    clauses[kw] = matched
        else:
            risk_terms = ["수습","삭감","강제","14시간","벌금","수당","무급","해고","경고","연장","자동"]
            for term in risk_terms:
                matched = [s for s in sents_full if term in s]
                if matched:
                    clauses[term] = matched
        return cat, summary, kws, clauses
    address = "서울특별시 중구 세종대로 110"  # 예시 주소
    naver_map_url = f"https://map.naver.com/v5/search/{address}"
    st.markdown(f"🔗 [네이버 지도에서 지적도 확인]({naver_map_url})", unsafe_allow_html=True)

    with st.expander("1) 외부 정보 조회", expanded=True):
        if contract_type == "부동산계약서":
            st.markdown("#### 주소로 지적도 조회")
            address = st.text_input("주소를 입력하세요", key="re_map_addr")
            if st.button("지적도 보기", key="re_map_btn") and address.strip():
                client_id = os.environ['NAVER_CLIENT_ID']  # 클라이언트 ID
                client_secret = os.environ['NAVER_CLIENT_SECRET']  # 시크릿 키
                url = f"https://maps.apigw.ntruss.com/map-geocode/v2/geocode?query={address}"
                headers = {
                    "X-NCP-APIGW-API-KEY-ID": client_id,
                    "X-NCP-APIGW-API-KEY": client_secret
                }
                res = requests.get(
                    url, headers=headers,
                )
                
                data = res.json()
                print(data)
                if data.get('addresses'):
                    lat = data['addresses'][0]['y']
                    lng = data['addresses'][0]['x']
                    print(lat, lng)
                    map_html = f"""
                    <script type="text/javascript" src="https://oapi.map.naver.com/openapi/v3/maps.js?ncpKeyId={client_id}"></script>
                    <div id="map" style="width:100%;height:400px;"></div>
                    <button id="cadastral" style="margin:10px;">지적도 끄기</button>
                    
                    <script>
                        var map = new naver.maps.Map('map', {{
                            center: new naver.maps.LatLng({lat}, {lng}),
                            zoom: 17,
                            mapTypeControl: true,
                              mapTypeControlOptions: {{
                                style: naver.maps.MapTypeControlStyle.DROPDOWN
                            }}
                        }});
                        var cadastralLayer = new naver.maps.CadastralLayer();
                        var btn = document.getElementById('cadastral');
                        naver.maps.Event.addListener(map, 'cadastralLayer_changed', function() {{
                            if (cadastralLayer.getMap()) {{
                                btn.classList.add('control-on');
                                btn.innerText = '지적도 끄기';
                            }} else {{
                                btn.classList.remove('control-on');
                                btn.innerText = '지적도 켜기';
                            }}
                        }});
                        btn.onclick = function(e) {{
                            e.preventDefault();
                            if (cadastralLayer.getMap()) {{
                                cadastralLayer.setMap(null);
                                btn.classList.remove('control-on');
                                btn.innerText = '지적도 켜기';
                            }} else {{
                                cadastralLayer.setMap(map);
                                btn.classList.add('control-on');
                                btn.innerText = '지적도 끄기';
                            }}
                        }};
                        naver.maps.Event.once(map, 'init', function() {{
                            cadastralLayer.setMap(map);
                        }});
                    </script>
                    """
                    st.components.v1.html(map_html, height=450)
                else:
                    st.warning("주소를 찾을 수 없습니다. 예: 서울특별시 중구 세종대로 110")

        else:
            search_key = f"defaulter_search_{state_key}"
            btn_key = f"btn_defaulter_search_{state_key}"
            search_name = st.text_input("사업장명으로 체불사업주 명단 검색", key=search_key)
            if st.button("명단 검색", key=btn_key):
                if not search_name.strip():
                    st.warning("검색어를 입력하세요.")
                else:
                    result = df_defaulters[df_defaulters['사업장명'].str.contains(search_name, case=False, na=False)]
                    if not result.empty:
                        st.success(f"🔎 '{search_name}' 관련 체불사업주 명단")
                        st.dataframe(result)
                    else:
                        st.info("해당 사업장명으로 등록된 체불사업주가 없습니다.")

    with st.expander("2) 계약서 파일 업로드"):
        uploaded = st.file_uploader("파일 업로드 (PDF/이미지)", key=f"upl_{state_key}")
        if uploaded and st.button("업로드 확인", key=f"btn_{state_key}_upl"):
            st.success(f"✅ 업로드된 파일: {uploaded.name}")
            st.session_state[f"{state_key}_step2"] = True
            st.session_state[f"{state_key}_text"] = extract_text_from_file(uploaded)

    with st.expander("3) 추출된 텍스트 확인 및 수정"):
        text = st.session_state.get(f"{state_key}_text", "")
        corrected = st.text_area("추출된 텍스트", text, key=f"txt_{state_key}", height=200)
        if st.button("수정 완료", key=f"btn_{state_key}_corr"):
            st.session_state[f"{state_key}_step3"] = True
            st.session_state[f"{state_key}_text"] = corrected

    with st.expander("4) 분석 결과 및 요약"):
        if st.session_state.get(f"{state_key}_step3"):
            text = st.session_state[f"{state_key}_text"]
            cat, summary, kws, clauses = analyze_contract(text)

            st.markdown("**1) 분류 결과**")
            st.write(f"예측 카테고리: {cat}")

            st.markdown("**2) 요약 결과**")
            st.write(summary)

            st.markdown("**3) 위험 키워드 탐지 및 조항**")
            if not clauses:
                st.write("위험 키워드 없음 및 잠정 조항 미검출")
            else:
                labels = kws if kws else list(clauses.keys())
                st.write(", ".join(labels))
                st.markdown("**문제 조항 상세**")
                for label in labels:
                    st.markdown(f"- **{label}**")
                    for seg in clauses[label]:
                        st.write(f"    - {seg.strip()}")

            st.markdown("**4) 원문 보기**")
            st.text_area("원문", text, height=200)
            st.session_state[f"{state_key}_step4"] = True
        else:
            st.info("3단계까지 완료하면 결과가 표시됩니다.")


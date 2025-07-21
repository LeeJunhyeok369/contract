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
from requests_toolbelt import MultipartEncoder
import uuid
import time

PAPAGO_CLIENT_ID = st.secrets["PAPAGO_CLIENT_ID"]
PAPAGO_CLIENT_SECRET = st.secrets["PAPAGO_CLIENT_SECRET"]

st.set_page_config(page_title="스마트 계약서 검토 시스템", layout="wide")

TEXTS = {
    "title": {
        "ko": "스마트 계약서 검토 시스템",
        "en": "Smart Contract Review System",
        "vi": "Hệ thống kiểm tra hợp đồng thông minh",
        "zh": "智能合同审核系统",
        "th": "ระบบตรวจสอบสัญญาอัจฉริยะ"
    },
    "onboard_title": {
        "ko": "이용 전 안내 및 동의",
        "en": "Notice & Agreement before using",
        "vi": "Lưu ý và đồng ý trước khi sử dụng",
        "zh": "使用前须知和同意",
        "th": "ข้อกำหนดก่อนใช้งานและข้อตกลง"
    },
    "onboard_desc": {
        "ko": """

- **개인정보 수집·이용 동의**  
제공하신 계약서, 주소 등 입력 데이터는 분석 결과 제공 용도로만 일시적으로 처리되며 별도 저장되지 않습니다.

- **참고용 서비스임에 대한 안내**  
본 AI 계약서 분석 서비스는 참고 자료로 제공되며, 법적 효력이나 책임은 발생하지 않습니다.  
최종 판단 및 법적 의무는 사용자 본인에게 있습니다.

위 내용(개인정보 동의 및 면책)에 모두 동의하셔야 서비스 이용이 가능합니다.
        """,
        "en": """
        
- **Agreement to Personal Data Collection/Use**  
Your input data (contract files, addresses, etc.) is processed only temporarily for analysis and not stored elsewhere.

- **Notice: This is a Reference Service Only**  
This AI contract review is for reference purposes only. It does **not** provide legal advice, and we are **not responsible** for any legal consequences.
The final judgment and all responsibility rest with the user.

You must agree to all the above (personal information and disclaimer) to use the service.
        """,
        "vi": """
        
- **Đồng ý thu thập và sử dụng thông tin cá nhân**  
Dữ liệu bạn nhập vào sẽ chỉ được xử lý tạm thời để phân tích và sẽ không lưu trữ lại.

- **Lưu ý: Đây chỉ là dịch vụ tham khảo**  
Kết quả phân tích này chỉ là tài liệu tham khảo, không có giá trị pháp lý và chúng tôi không chịu trách nhiệm pháp lý nào.
Quyết định cuối cùng và mọi trách nhiệm thuộc về người dùng.

Bạn phải đồng ý với tất cả nội dung trên để sử dụng dịch vụ.
        """,
        "zh": """
        
- **同意个人信息收集和使用**  
您输入的合同、地址等仅用于分析，不会被存储。

- **仅供参考的免责声明**  
本AI合同分析服务仅供参考，不具有法律效力，我们不承担任何责任。
最终决策和一切法律责任归用户本人所有。

只有同意以上内容，才能使用本服务。
        """,
        "th": """
        
- **ความยินยอมในการเก็บและใช้ข้อมูลส่วนบุคคล**  
ข้อมูลที่ท่านระบุจะถูกใช้เพื่อการวิเคราะห์ชั่วคราวและจะไม่ถูกจัดเก็บ

- **ข้อมูลเพื่อการอ้างอิงเท่านั้น/ไม่มีความรับผิดชอบทางกฎหมาย**  
บริการนี้เป็นเพียงการอ้างอิง ไม่มีผลผูกพันทางกฎหมาย ผู้พัฒนาจะไม่รับผิดชอบผลใดๆ ทั้งสิ้น
ผู้ใช้ต้องรับผิดชอบในการตัดสินใจและผลลัพธ์เอง

ต้องยอมรับเงื่อนไขข้างต้นก่อนจึงจะสามารถใช้งานบริการนี้ได้
        """
    },
    "onboard_agree_btn": {
        "ko": "동의합니다 (서비스 시작)",
        "en": "I Agree (Start Service)",
        "vi": "Tôi đồng ý (Bắt đầu sử dụng)",
        "zh": "我同意（开始使用）",
        "th": "ยอมรับและเริ่มใช้งาน"
    },
    "subtitle": {
        "ko": "AI 기반 계약서 분석으로 안전한 계약을 도와드립니다",
        "en": "Helping safe contracts through AI-based document analysis",
        "vi": "Hỗ trợ hợp đồng an toàn bằng phân tích hợp đồng dựa trên AI",
        "zh": "通过AI分析合同，助您签署安全合同",
        "th": "ช่วยตรวจสอบสัญญาให้ปลอดภัยด้วย AI"
    },
    "contract_choice_emp": {
        "ko": "근로계약서",
        "en": "Employment Contract",
        "vi": "Hợp đồng lao động",
        "zh": "劳动合同",
        "th": "สัญญาจ้างงาน"
    },
    "contract_choice_emp_desc": {
        "ko": "근로 조건, 임금, 근무 시간 등 노동 관련 계약 분석",
        "en": "Analyze labor conditions, wages, and working hours",
        "vi": "Phân tích điều kiện lao động, tiền lương và thời gian làm việc",
        "zh": "分析劳动条件、工资、工时等劳务合同",
        "th": "วิเคราะห์เงื่อนไขการทำงาน ค่าจ้าง ชั่วโมงทำงานและสัญญาแรงงาน"
    },
    "contract_choice_re": {
        "ko": "부동산계약서",
        "en": "Real Estate Contract",
        "vi": "Hợp đồng bất động sản",
        "zh": "房地产合同",
        "th": "สัญญาอสังหาริมทรัพย์"
    },
    "contract_choice_re_desc": {
        "ko": "임대차, 매매 등 부동산 계약서 분석 및 지도 조회",
        "en": "Analysis of leases, sales, and real estate contracts with map search",
        "vi": "Phân tích hợp đồng bất động sản và tra cứu bản đồ",
        "zh": "分析租赁、买卖等房地产合同及地图检索",
        "th": "วิเคราะห์สัญญาเช่า-ซื้อ และอสังหาริมทรัพย์ พร้อมค้นหาแผนที่"
    },
    "select_emp": {
        "ko": "근로계약서 선택",
        "en": "Select Employment Contract",
        "vi": "Chọn hợp đồng lao động",
        "zh": "选择劳动合同",
        "th": "เลือกสัญญาจ้างงาน"
    },
    "select_re": {
        "ko": "부동산계약서 선택",
        "en": "Select Real Estate Contract",
        "vi": "Chọn hợp đồng bất động sản",
        "zh": "选择房地产合同",
        "th": "เลือกสัญญาอสังหาริมทรัพย์"
    },
    "workflow": {
        "ko": "{} 워크플로우",
        "en": "{} Workflow",
        "vi": "Quy trình {}",
        "zh": "{} 工作流程",
        "th": "กระบวนการ {}"
    },
    "external_info": {
        "ko": "1) 외부 정보 조회",
        "en": "1) External Information Lookup",
        "vi": "1) Tra cứu thông tin bên ngoài",
        "zh": "1) 外部信息调用",
        "th": "1) ค้นหาข้อมูลภายนอก"
    },
    "address_search_title": {
        "ko": "주소로 지적도 지도 검색",
        "en": "Search Cadastral Map by Address",
        "vi": "Tra cứu bản đồ địa chính theo địa chỉ",
        "zh": "按地址查询地籍图",
        "th": "ค้นหาแผนที่ที่ดินด้วยที่อยู่"
    },
    "address_input": {
        "ko": "주소를 입력하세요",
        "en": "Enter Address",
        "vi": "Nhập địa chỉ",
        "zh": "请输入地址",
        "th": "กรอกที่อยู่"
    },
    "address_search_btn": {
        "ko": "주소 검색 및 지도 이동",
        "en": "Search Address and Move Map",
        "vi": "Tìm kiếm địa chỉ và dịch chuyển bản đồ",
        "zh": "搜索地址并移动地图",
        "th": "ค้นหาที่อยู่และเลื่อนแผนที่"
    },
    "addr_input_warning": {
        "ko": "주소를 입력해주세요.",
        "en": "Please enter an address.",
        "vi": "Vui lòng nhập địa chỉ.",
        "zh": "请输入地址。",
        "th": "กรุณากรอกที่อยู่"
    },
    "addr_success": {
        "ko": "주소 변환 성공: {} (경도: {:.5f}, 위도: {:.5f})",
        "en": "Address converted successfully: {} (Lng: {:.5f}, Lat: {:.5f})",
        "vi": "Chuyển đổi địa chỉ thành công: {} (Kinh độ: {:.5f}, Vĩ độ: {:.5f})",
        "zh": "地址转换成功：{}（经度：{:.5f}，纬度：{:.5f}）",
        "th": "แปลงที่อยู่สำเร็จ: {} (ลองจิจูด: {:.5f}, ละติจูด: {:.5f})"
    },
    "addr_fail": {
        "ko": "지적도 끄기",
        "en": "Turn off the intellectual map",
        "vi": "Tắt bản đồ địa chính",
        "zh": "关闭地籍图",
        "th": "ปิดแผนที่ที่ดิน"
    },
    "addr_fail2": {
        "ko": "지적도 켜기",
        "en": "Turn on the intellectual map",
        "vi": "Bật bản đồ địa chính",
        "zh": "打开地籍图",
        "th": "เปิดแผนที่ที่ดิน"
    },
    "search_defaulter": {
        "ko": "사업장명으로 체불사업주 명단 검색",
        "en": "Search Defaulter List by Business Name",
        "vi": "Tìm danh sách chủ doanh nghiệp nợ lương theo tên doanh nghiệp",
        "zh": "按企业名称查询拖欠工资企业名单",
        "th": "ค้นหารายชื่อบริษัทที่ค้างค่าจ้างตามชื่อบริษัท"
    },
    "search_defaulter_btn": {
        "ko": "명단 검색",
        "en": "Search List",
        "vi": "Tìm kiếm danh sách",
        "zh": "查询名单",
        "th": "ค้นหารายชื่อ"
    },
    "search_keyword_warning": {
        "ko": "검색어를 입력하세요.",
        "en": "Please enter a search term.",
        "vi": "Vui lòng nhập từ khóa tìm kiếm.",
        "zh": "请输入搜索关键词。",
        "th": "กรุณากรอกคำค้นหา"
    },
    "search_result_found": {
        "ko": "🔎 '{}' 관련 체불사업주 명단",
        "en": "🔎 Defaulter list related to '{}'",
        "vi": "🔎 Danh sách chủ doanh nghiệp nợ lương liên quan đến '{}'",
        "zh": "🔎 与'{}'相关的拖欠工资企业名单",
        "th": "🔎 รายชื่อบริษัทที่ค้างค่าจ้างเกี่ยวข้องกับ '{}'"
    },
    "search_result_none": {
        "ko": "해당 사업장명으로 등록된 체불사업주가 없습니다.",
        "en": "No defaulters registered under that business name.",
        "vi": "Không có chủ doanh nghiệp nợ lương được đăng ký với tên đó.",
        "zh": "该企业名称下未注册拖欠工资企业。",
        "th": "ไม่มีบริษัทที่ค้างค่าจ้างที่ลงทะเบียนในชื่อนี้"
    },
    "file_upload": {
        "ko": "2) 계약서 파일 업로드",
        "en": "2) Upload Contract File",
        "vi": "2) Tải lên tệp hợp đồng",
        "zh": "2) 上传合同文件",
        "th": "2) อัปโหลดไฟล์สัญญา"
    },
    "file_uploader": {
        "ko": "파일 업로드 (PDF/이미지)",
        "en": "Upload File (PDF/Image)",
        "vi": "Tải lên tệp (PDF/Ảnh)",
        "zh": "上传文件（PDF/图片）",
        "th": "อัปโหลดไฟล์ (PDF/รูปภาพ)"
    },
    "upload_confirm_btn": {
        "ko": "업로드 확인",
        "en": "Confirm Upload",
        "vi": "Xác nhận tải lên",
        "zh": "确认上传",
        "th": "ยืนยันการอัปโหลด"
    },
    "file_uploaded": {
        "ko": "✅ 업로드된 파일: {}",
        "en": "✅ Uploaded file: {}",
        "vi": "✅ Tệp đã tải lên: {}",
        "zh": "✅ 上传的文件：{}",
        "th": "✅ ไฟล์ที่อัปโหลด: {}"
    },
    "text_confirm": {
        "ko": "3) 추출된 텍스트 확인 및 수정",
        "en": "3) Check and Edit Extracted Text",
        "vi": "3) Kiểm tra và chỉnh sửa văn bản trích xuất",
        "zh": "3) 检查并编辑提取的文本",
        "th": "3) ตรวจสอบและแก้ไขข้อความที่สกัดได้"
    },
    "extracted_text": {
        "ko": "추출된 텍스트",
        "en": "Extracted Text",
        "vi": "Văn bản đã trích xuất",
        "zh": "提取的文本",
        "th": "ข้อความที่สกัดได้"
    },
    "text_edit_done_btn": {
        "ko": "수정 완료",
        "en": "Complete Edit",
        "vi": "Hoàn thành chỉnh sửa",
        "zh": "完成编辑",
        "th": "เสร็จสิ้นการแก้ไข"
    },
    "analysis_results": {
        "ko": "4) 분석 결과 및 요약",
        "en": "4) Analysis Results and Summary",
        "vi": "4) Kết quả phân tích và tóm tắt",
        "zh": "4) 分析结果及总结",
        "th": "4) ผลวิเคราะห์และสรุป"
    },
    "step3_incomplete": {
        "ko": "3단계까지 완료하면 결과가 표시됩니다.",
        "en": "Complete step 3 to display results.",
        "vi": "Hoàn thành bước 3 để hiển thị kết quả.",
        "zh": "完成第3步后将显示结果。",
        "th": "กรุณาดำเนินการถึงขั้นตอนที่ 3 ก่อนจะแสดงผลลัพธ์"
    },
    "summary_result": {
        "ko": "**1) 요약 결과**",
        "en": "**1) Summary**",
        "vi": "**1) Kết quả tóm tắt**",
        "zh": "**1) 总结结果**",
        "th": "**1) ผลสรุป**"
    },
    "risk_keywords": {
        "ko": "**2) 위험 키워드 탐지 및 조항**",
        "en": "**2) Detected Risk Keywords and Clauses**",
        "vi": "**2) Từ khóa & điều khoản có rủi ro**",
        "zh": "**2) 检测到的风险关键词和条款**",
        "th": "**2) คำสำคัญ/ข้อกำหนดเสี่ยงที่ตรวจพบ**"
    },
    "no_risk_keywords": {
        "ko": "위험 키워드 없음 및 잠정 조항 미검출",
        "en": "No risk keywords or clauses detected.",
        "vi": "Không phát hiện từ khóa hoặc điều khoản rủi ro.",
        "zh": "未检测到风险关键词或条款。",
        "th": "ไม่พบคำสำคัญหรือข้อเสี่ยง"
    },
    "problem_clause_detail": {
        "ko": "**문제 조항 상세**",
        "en": "**Detailed Problematic Clauses**",
        "vi": "**Chi tiết điều khoản có vấn đề**",
        "zh": "**问题条款详情**",
        "th": "**รายละเอียดข้อที่มีปัญหา**"
    },
    "original_text": {
        "ko": "**4) 원문 보기**",
        "en": "**4) Original Text**",
        "vi": "**4) Xem bản gốc**",
        "zh": "**4) 查看原文**",
        "th": "**4) ดูข้อความต้นฉบับ**"
    },
    "original_text_area": {
        "ko": "원문",
        "en": "Original Text",
        "vi": "Văn bản gốc",
        "zh": "原文",
        "th": "ต้นฉบับ"
    },
    "standard_dictionary_expander": {
        "ko": "🔍 표준국어대사전 & 우리말샘 동시검색",
        "en": "🔍 Standard Korean Dictionary & Woorimal Saem Dual Search",
        "vi": "🔍 Tra cứu song song từ điển tiêu chuẩn & Woorimal Saem",
        "zh": "🔍 标准韩国语词典 & Woorimal Saem 同时搜索",
        "th": "🔍 ค้นหาพจนานุกรมเกาหลีมาตรฐาน & Woorimal Saem พร้อมกัน"
    },
    "search_word_input": {
        "ko": "검색어(한 단어만 입력): 두 사전에서 동시에 조회",
        "en": "Search word (single word only): simultaneous lookup in two dictionaries",
        "vi": "Nhập từ cần tra (chỉ một từ): tra cứu đồng thời 2 từ điển",
        "zh": "输入查询词（只输入一个词）：在两词典同时查询",
        "th": "กรอกคำค้น (เพียงหนึ่งคำ): ค้นหาในพจนานุกรมทั้งสองพร้อมกัน"
    },
    "search_both_btn": {
        "ko": "두 사전 동시검색",
        "en": "Search both dictionaries",
        "vi": "Tra cứu cả 2 từ điển",
        "zh": "同时搜索两词典",
        "th": "ค้นหาทั้งสองพจนานุกรม"
    },
    "search_word_warning": {
        "ko": "검색어를 입력하세요.",
        "en": "Please enter a search word.",
        "vi": "Vui lòng nhập từ cần tra cứu.",
        "zh": "请输入查询词。",
        "th": "กรุณากรอกคำที่ต้องการค้นหา"
    },
    "dict_response_error": {
        "ko": "대사전 응답 오류 또는 파싱 오류",
        "en": "Dictionary response error or parsing error",
        "vi": "Lỗi phản hồi hoặc phân tích dữ liệu từ điển",
        "zh": "词典响应错误或解析错误",
        "th": "เกิดข้อผิดพลาดในการตอบสนองหรือแยกวิเคราะห์พจนานุกรม"
    },
    "no_search_result": {
        "ko": "검색 결과가 없습니다.",
        "en": "No results found.",
        "vi": "Không có kết quả.",
        "zh": "未找到结果。",
        "th": "ไม่พบผลลัพธ์"
    },
    "standard_dictionary_title": {
        "ko": "📚 표준국어대사전",
        "en": "📚 Standard Korean Dictionary",
        "vi": "📚 Từ điển Quốc ngữ chuẩn",
        "zh": "📚 标准韩国语词典",
        "th": "📚 พจนานุกรมเกาหลีมาตรฐาน"
    },
    "woorimal_dictionary_title": {
        "ko": "📖 우리말샘",
        "en": "📖 Woorimal Saem Dictionary",
        "vi": "📖 Từ điển Wooorimal Saem",
        "zh": "📖 Woorimal Saem 词典",
        "th": "📖 พจนานุกรม Woorimal Saem"
    },
    "dictionary_source_caption_std": {
        "ko": "출처: 표준국어대사전 Open API",
        "en": "Source: Standard Korean Dictionary Open API",
        "vi": "Nguồn: API Từ điển Quốc ngữ chuẩn",
        "zh": "来源：标准韩国语词典 Open API",
        "th": "ที่มา: มาตรฐานพจนานุกรมเกาหลี Open API"
    },
    "dictionary_source_caption_oms": {
        "ko": "출처: 우리말샘 Open API",
        "en": "Source: Woorimal Saem Open API",
        "vi": "Nguồn: API Woorimal Saem",
        "zh": "来源：Woorimal Saem Open API",
        "th": "ที่มา: Woorimal Saem Open API"
    },
    "translation": {
        "ko": "🔍MyMemory 번역",
        "en": "🔍 Translation of MyMemory",
        "vi": "🔍 Dịch sang My Memory",
        "zh": "🔍 MyMemory 翻译",
        "th": "🔍 แปลด้วย MyMemory"
    },
    "msg0": {
        "ko": "안전성이 높은 계약서 입니다.",
        "en": "This contract is highly secure.",
        "vi": "Đây là hợp đồng có độ an toàn cao.",
        "zh": "这是安全性很高的合同。",
        "th": "นี่คือสัญญาที่มีความปลอดภัยสูง"
    },
    "msg10": {
        "ko": "위험조항이 일부 검출되었으니 계약서를 다시 검토해 주세요.",
        "en": "Some risky clauses have been detected. Please review the contract again.",
        "vi": "Một số điều khoản rủi ro đã được phát hiện. Vui lòng xem xét hợp đồng lại.",
        "zh": "检测到部分风险条款，请重新审核合同。",
        "th": "ตรวจพบข้อที่มีความเสี่ยงบางส่วน กรุณาตรวจสอบสัญญาอีกครั้ง"
    },
    "msg30": {
        "ko": "다량의 위험조항이 발견되었습니다. 계약을 권고하지 않습니다.",
        "en": "Numerous risky clauses have been found. The contract is not recommended.",
        "vi": "Phát hiện nhiều điều khoản rủi ro. Không khuyến nghị ký hợp đồng này.",
        "zh": "发现大量风险条款。不建议签署该合同。",
        "th": "พบข้อที่มีความเสี่ยงเป็นจำนวนมาก ไม่แนะนำให้ทำสัญญานี้"
    },
    "msg50": {
        "ko": "계약서 대부분이 위험조항으로 검출되었습니다.",
        "en": "Most of the contract has been identified as containing risky clauses.",
        "vi": "Phần lớn hợp đồng bị phát hiện có điều khoản rủi ro.",
        "zh": "合同的大部分内容被检测为风险条款。",
        "th": "พบว่าส่วนใหญ่ของสัญญานี้มีข้อที่มีความเสี่ยง"
    },
    "onboard_agree_btn": {"ko": "동의합니다 (서비스 시작)", "en": "I Agree (Start Service)", "vi": "Tôi đồng ý (Bắt đầu sử dụng)", "zh": "我同意（开始使用）", "th": "ยอมรับและเริ่มใช้งาน"},
    "back_btn": {"ko": "선택 화면으로 돌아가기", "en": "Back to main selection", "vi": "Quay lại chọn loại hợp đồng", "zh": "返回合同选择", "th": "◀ กลับไปเลือกสัญญา"},
    "onboard_cancel_btn": {
        "ko": "취소",
        "en": "Cancel",
        "vi": "Huỷ",
        "zh": "取消",
        "th": "ยกเลิก"
    },
    "lang_name": {
        "en": "English",
        "ko": "영어",
        "vi": "tiếng Việt",
        "zh": "英文",
        "th": "ภาษาอังกฤษ"
    },
    "lang_name_ko": {
        "en": "Korean",
        "ko": "한국어",
        "vi": "tiếng Hàn",
        "zh": "韩文",
        "th": "ภาษาเกาหลี"
    },
    "lang_name_vi": {
        "en": "Vietnamese",
        "ko": "베트남어",
        "vi": "tiếng Việt",
        "zh": "越南语",
        "th": "ภาษาเวียดนาม"
    },
    "lang_name_zh": {
        "en": "Chinese",
        "ko": "중국어",
        "vi": "tiếng Trung",
        "zh": "中文",
        "th": "ภาษาจีน"
    },
    "lang_name_th": {
        "en": "Thai",
        "ko": "태국어",
        "vi": "tiếng Thái",
        "zh": "泰语",
        "th": "ภาษาไทย"
    },
    "pdf_translate_title": {
        "ko": "🇰🇷 PDF → 사이트 언어 번역 & 다운로드",
        "en": "🇰🇷 PDF → Translate to selected language & download",
        "vi": "🇰🇷 PDF → Dịch sang ngôn ngữ của trang & tải xuống",
        "zh": "🇰🇷 PDF → 翻译为所选语言并下载",
        "th": "🇰🇷 PDF → แปลเป็นภาษาที่เลือก & ดาวน์โหลด"
    },
    "btn_pdf_translate": {
        "ko": "한국어 PDF를 {}로 번역/다운로드",
        "en": "Translate Korean PDF to {} & download",
        "vi": "Dịch PDF tiếng Hàn sang {} & tải xuống",
        "zh": "将韩文PDF翻译为{}并下载",
        "th": "แปล PDF ภาษาเกาหลีเป็น {} และดาวน์โหลด"
    },
    "pdf_translate_success": {
        "ko": "번역 완료! ({})",
        "en": "Translation complete! ({})",
        "vi": "Dịch hoàn tất! ({})",
        "zh": "翻译完成! ({})",
        "th": "แปลเสร็จสิ้น! ({})"
    },
    "pdf_download_button": {
        "ko": "번역된 PDF 다운로드 ({})",
        "en": "Download translated PDF ({})",
        "vi": "Tải PDF đã dịch ({})",
        "zh": "下载翻译后的PDF ({})",
        "th": "ดาวน์โหลด PDF ที่แปลแล้ว ({})"
    },
    "pdf_translate_inprogress": {
        "ko": "{} 번역 생성 중... (최대 2분 소요)",
        "en": "Translating to {}... (may take up to 2 min)",
        "vi": "Đang tạo bản dịch sang {}... (tối đa 2 phút)",
        "zh": "正在翻译为{}...（最多2分钟）",
        "th": "กำลังแปลเป็น {}... (สูงสุด 2 นาที)"
    },
    "pdf_translate_fail": {
        "ko": "Papago 번역 실패",
        "en": "Papago translation failed",
        "vi": "Dịch Papago thất bại",
        "zh": "Papago翻译失败",
        "th": "การแปลด้วย Papago ล้มเหลว"
    },
    "pdf_translate_slow": {
        "ko": "Papago 번역 지연/실패",
        "en": "Papago translation delayed/failed",
        "vi": "Dịch Papago bị chậm/không thành công",
        "zh": "Papago翻译延迟/失败",
        "th": "การแปลด้วย Papago ช้าหรือผิดพลาด"
    },
    "pdf_translate_req_fail": {
        "ko": "Papago 번역 요청 실패",
        "en": "Papago translation request failed",
        "vi": "Yêu cầu dịch Papago thất bại",
        "zh": "Papago翻译请求失败",
        "th": "คำขอแปล Papago ล้มเหลว"
    },

}



def papago_translate(text, target_lang):
    if target_lang == "en":
        target = "en"
    elif target_lang == "vi":
        target = "vi"
    elif target_lang == "zh":
        target = "zh-CN"
    elif target_lang == "th":
        target = "th"
    else:
        return text
    url = "https://papago.apigw.ntruss.com/nmt/v1/translation"
    headers = {
        "X-NCP-APIGW-API-KEY-ID": PAPAGO_CLIENT_ID,
        "X-NCP-APIGW-API-KEY": PAPAGO_CLIENT_SECRET
    }
    data = {"source": "ko", "target": target, "text": text}
    if not text.strip():
        return ""
    try:
        res = requests.post(url, headers=headers, data=data, timeout=8)
        if res.status_code == 200:
            return res.json()['message']['result']['translatedText']
        else:
            return f"(Papago 번역 실패: {res.status_code})"
    except Exception:
        return "(Papago 번역 에러)"

def tt(key, *fmt):
    lang = st.session_state.get("lang", "ko")
    text = TEXTS.get(key, {}).get(lang, TEXTS.get(key, {}).get("ko", ""))
    if fmt:
        return text.format(*fmt)
    return text

@st.cache_data
def load_defaulter_data(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    df['체불액(원)'] = df['체불액(원)'].str.replace(',', '').astype(int)
    return df

DEFAULTER_JSON_PATH = "./defaulter_list.json"
df_defaulters = load_defaulter_data(DEFAULTER_JSON_PATH)
KEYWORD_EXCEL_PATH = r"./불공정_키워드_표형식_단어쪼개기_186x20.xlsx"
detector = KeywordDetector(KEYWORD_EXCEL_PATH)

KAKAO_REST_API_KEY = st.secrets["KAKAO_REST_API_KEY"]
KAKAO_JS_KEY = st.secrets["KAKAO_JS_KEY"]

if "lang" not in st.session_state:
    st.session_state["lang"] = "ko"
def change_language():
    st.session_state['lang'] = lang_options[st.session_state['lang_select']]
    st.rerun()

with st.sidebar:
    lang_options = {
        "한국어": "ko", "English": "en", "Tiếng Việt": "vi", "简体中文": "zh", "ภาษาไทย": "th"
    }
    current_lang_label = [k for k, v in lang_options.items() if v == st.session_state["lang"]][0]
    st.selectbox(
        "언어 선택 / Language",
        list(lang_options.keys()),
        key='lang_select',
        index=list(lang_options.keys()).index(current_lang_label),
        on_change=change_language,
    )

if "contract_type" not in st.session_state:
    st.session_state["contract_type"] = None

# ---- Dialog 기반 동의 모달 ----
@st.dialog(tt('onboard_title'), width="small")
def show_agreement_dialog(contract_type):
    st.markdown(tt('onboard_desc'))
    col1, col2 = st.columns(2)
    with col1:
        if st.button(tt("onboard_agree_btn"), use_container_width=True):
            st.session_state["contract_type"] = contract_type
            st.rerun()
    with col2:
        if st.button(tt("onboard_cancel_btn"), use_container_width=True):
            st.session_state["contract_type"] = None
            st.rerun()

def kakao_geocode(address, rest_api_key):
    url = "https://dapi.kakao.com/v2/local/search/address.json"
    headers = {"Authorization": f"KakaoAK {rest_api_key}"}
    params = {"query": address}
    try:
        res = requests.get(url, headers=headers, params=params)
        data = res.json()
    except Exception:
        return None, None, None
    if data.get("documents"):
        doc = data["documents"][0]
        x = float(doc["x"])
        y = float(doc["y"])
        road_addr = doc.get("road_address") or doc.get("address")
        road = road_addr["address_name"] if road_addr else ""
        return x, y, road
    return None, None, None

def extract_text_from_file(uploaded):
    fname = uploaded.name.lower()
    if fname.endswith(".pdf"):
        with pdfplumber.open(uploaded) as pdf:
            pages = [p.extract_text() or "" for p in pdf.pages]
        return "\n\n".join(pages)
    elif any(fname.endswith(ext) for ext in ["png", "jpg", "jpeg"]):
        return pytesseract.image_to_string(Image.open(uploaded), lang="kor+eng")
    else:
        return uploaded.read().decode("utf-8", errors="ignore")

def analyze_contract(text):
    try:
        cat = predict(text)
    except:
        cat = tt("classification_result")  # fallback 분류 실패 메시지
    sents = [s.strip() for s in text.replace("?", ".").split(".") if len(s.strip()) > 20]
    summary = ". ".join(sents[:3]) + ("…" if len(sents) > 3 else "")
    try:
        kws = detector.detect(text)
    except:
        kws = []
    clauses = {}
    sents_full = re.split(r'(?<=[.?!])\s+', text)
    seen = set()
    if kws:
        for kw in kws:
            matches = [sent for sent in sents_full if sent not in seen and re.search(rf"\b{re.escape(kw)}\b", sent)]
            seen.update(matches)
            if matches:
                clauses[kw] = matches
    else:
        risk_terms = ["수습", "삭감", "강제", "14시간", "벌금", "수당", "무급", "해고", "경고", "연장", "자동"]
        for term in risk_terms:
            matches = [sent for sent in sents_full if sent not in seen and term in sent]
            seen.update(matches)
            if matches:
                clauses[term] = matches
    return cat, summary, kws, clauses

def get_papago_target_lang(lang):
    return {
        "ko": "en",
        "en": "en",
        "vi": "vi",
        "zh": "zh-CN",
        "th": "th",
    }.get(lang, "en")  # ko인 경우 영문

def translate_pdf_with_papago(pdf_bytes, filename, target_lang):
    api_url = "https://papago.apigw.ntruss.com/doc-trans/v1/translate"
    data = {
        'source': 'ko',  # 한글 고정
        'target': target_lang,
        'file': (filename, pdf_bytes, 'application/pdf', {'Content-Transfer-Encoding': 'binary'})
    }
    m = MultipartEncoder(data, boundary=uuid.uuid4().hex)
    headers = {
        "Content-Type": m.content_type,
        "X-NCP-APIGW-API-KEY-ID": PAPAGO_CLIENT_ID,
        "X-NCP-APIGW-API-KEY": PAPAGO_CLIENT_SECRET
    }
    res = requests.post(api_url, headers=headers, data=m.to_string())
    if res.status_code != 200:
        st.error(f"PDF 번역 요청 실패: {res.status_code}")
        st.write(res.text)
        print(res.text)
        return None
    else:
        print(res.json())
    return res.json().get('data', {}).get('requestId')

def check_translation_status(request_id):
    api_url = f"https://papago.apigw.ntruss.com/doc-trans/v1/status?requestId={request_id}"
    headers = {
        "X-NCP-APIGW-API-KEY-ID": PAPAGO_CLIENT_ID,
        "X-NCP-APIGW-API-KEY": PAPAGO_CLIENT_SECRET,
    }
    res = requests.get(api_url, headers=headers)
    if res.status_code != 200:
        return None, None
    result = res.json()
    data = result.get("data", {})
    return data.get("status")

def download_translated_pdf(request_id):
    url = f"https://papago.apigw.ntruss.com/doc-trans/v1/download?requestId={request_id}"
    headers = {
        "X-NCP-APIGW-API-KEY-ID": PAPAGO_CLIENT_ID,
        "X-NCP-APIGW-API-KEY": PAPAGO_CLIENT_SECRET,
    }
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        return resp.content
    else:
        st.error(f"Papago 변환 파일 다운로드 실패: {resp.status_code}")
        return None

def summarize_text_perplexity(text):
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": "Bearer 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",
        "Content-Type": "application/json"
    }
    data = {
        "model": "sonar-pro",
        "messages": [
            {"role": "system", "content": "다음 계약서 내용을 간결하게 요약해줘."},
            {"role": "user", "content": text}
        ],
        "max_tokens": 500,
        "temperature": 0.7
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code != 200:
        print("API 호출 실패:", response.status_code)
        print("응답 내용:", response.text)
        return None
    try:
        result = response.json()
        if 'choices' not in result:
            print("API 응답에 'choices' 키가 없습니다. 전체 응답:", result)
            return None
        return result['choices'][0]['message']['content']
    except Exception as e:
        print("JSON 파싱 오류:", e)
        print("응답 내용:", response.text)
        return None
    
def get_display_lang_name(target_lang, page_lang):
    mapping_key = {
        "en": "lang_name",
        "ko": "lang_name_ko",
        "vi": "lang_name_vi",
        "zh-CN": "lang_name_zh",
        "th": "lang_name_th"
    }[target_lang]
    return TEXTS[mapping_key][page_lang]

# ================== 메인화면 ===================
st.markdown(f"""
    <h1 style="text-align:center;color:#222;font-weight:700;">{tt('title')}</h1>
    <p style="text-align:center;color:#888;font-size:1.1em;">{tt('subtitle')}</p>
""", unsafe_allow_html=True)
st.markdown("""
<style>
.choice-card { background: #fff; border: 1.5px solid #e2e2e2; border-radius: 16px; padding: 32px 18px;
    margin-bottom: 10px; box-shadow: 0 2px 12px #f2f2f2; text-align: center;}
.choice-card:hover { border: 1.5px solid #aaa; }
.choice-btn { width: 100%; padding: 22px; background: #f9f9f9; color: #222; border: 1.5px solid #eee;
    border-radius: 12px; font-size: 1.25em; font-weight: 600; box-shadow: 0 2px 8px #ececec;}
.btn-desc { margin-top: 14px; font-size: 1.05em; color: #888;}
.stButton button { width: 100%; display: block; }
#toggle_cadastral {width: 100%; display: block;}
</style>
""", unsafe_allow_html=True)

if st.session_state["contract_type"] is None:
    col1, col2 = st.columns(2, gap="large")
    with col1:
        st.markdown(f"""
        <div class="choice-card">
            <h3 class="choice-btn">{tt('contract_choice_emp')}</h3>
            <div class="btn-desc">{tt('contract_choice_emp_desc')}</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button(tt("select_emp")):
            show_agreement_dialog("emp")
    with col2:
        st.markdown(f"""
        <div class="choice-card">
            <h3 class="choice-btn">{tt('contract_choice_re')}</h3>
            <div class="btn-desc">{tt('contract_choice_re_desc')}</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button(tt("select_re")):
            show_agreement_dialog("re")
    st.stop()
else:
    if st.button(tt("back_btn")):
        st.session_state["contract_type"] = None
        st.rerun()
    contract_type = st.session_state["contract_type"]
    state_key = contract_type
    st.markdown(tt("workflow").format(tt(
        "contract_choice_emp" if contract_type == "emp" else "contract_choice_re"
    )))

    with st.expander(tt("external_info"), expanded=True):
        if contract_type == "re":
            st.markdown(f"#### {tt('address_search_title')}")
            address = st.text_input(tt("address_input"), key="re_map_addr")
            if 'map_coords' not in st.session_state:
                st.session_state['map_coords'] = (37.5665, 126.978)
            if st.button(tt("address_search_btn"), key="btn_addr_search"):
                if not address.strip():
                    st.warning(tt("addr_input_warning"))
                    st.session_state['map_coords'] = (37.5665, 126.978)
                else:
                    x, y, road = kakao_geocode(address, KAKAO_REST_API_KEY)
                    if x and y:
                        st.success(tt("addr_success").format(road, x, y))
                        st.session_state['map_coords'] = (y, x)
                    else:
                        st.error(tt("addr_fail"))
                        st.session_state['map_coords'] = (37.5665, 126.978)
            map_lat, map_lng = st.session_state.get('map_coords', (37.5665, 126.978))
            st.components.v1.html(f"""
                <style>
                    #toggle_cadastral {{
                        width: 100%;
                        padding: 13px 0;
                        font-size: 1.07em;
                        font-weight: 600;
                        border: none;
                        border-radius: 8px;
                        background: #f1f4fa;
                        color: #174CA1;
                        margin-top: 8px;
                        cursor: pointer;
                        box-shadow: 0 2px 8px #e0e7ef;
                        transition: background 0.2s, color 0.2s;
                        outline: none;
                    }}
                    #toggle_cadastral:hover {{
                        background: #174CA1;
                        color: #fff;
                    }}
                    #toggle_cadastral:active {{
                        background: #0e295c;
                        color: #fff;
                    }}
                </style>
                <div id="map" style="width:100%;height:400px;border-radius:8px;"></div>
                <div style="margin-top:10px;">
                    <button id="toggle_cadastral" class="">{tt('addr_fail')}</button>
                </div>
                <script src="https://dapi.kakao.com/v2/maps/sdk.js?appkey={KAKAO_JS_KEY}&libraries=services"></script>
                <script>
                let map, cadastral, kakaoMarker = null;
                window.onload = function () {{
                    var container = document.getElementById('map');
                    var center = new kakao.maps.LatLng({map_lat}, {map_lng});
                    var options = {{
                        center: center,
                        level: 1
                    }};
                    map = new kakao.maps.Map(container, options);
                    map.addOverlayMapTypeId(kakao.maps.MapTypeId.USE_DISTRICT);
                    var markerPosition  = new kakao.maps.LatLng({map_lat}, {map_lng});
                    kakaoMarker = new kakao.maps.Marker({{
                        position: markerPosition,
                        map: map
                    }});
                    document.getElementById("toggle_cadastral").onclick = function () {{
                        if (this.innerText == '{tt("addr_fail")}') {{
                            map.removeOverlayMapTypeId(kakao.maps.MapTypeId.USE_DISTRICT);
                            this.innerText = '{tt("addr_fail2")}';
                        }} else {{
                            map.addOverlayMapTypeId(kakao.maps.MapTypeId.USE_DISTRICT);
                            this.innerText = '{tt("addr_fail")}';
                        }}
                    }};
                }};
                </script>
            """, height=480)
        else:
            search_key = f"defaulter_search_{state_key}"
            btn_key = f"btn_defaulter_search_{state_key}"
            search_name = st.text_input(tt("search_defaulter"), key=search_key)
            if st.button(tt("search_defaulter_btn"), key=btn_key):
                if not search_name.strip():
                    st.warning(tt("search_keyword_warning"))
                else:
                    result = df_defaulters[df_defaulters['사업장명'].str.contains(search_name, case=False, na=False)]
                    if not result.empty:
                        st.success(tt("search_result_found").format(search_name))
                        st.dataframe(result)
                    else:
                        st.info(tt("search_result_none"))

    # ----- 여기부터 Papago Doc 번역 기능 -----
    with st.expander(tt("file_upload")):
        uploaded = st.file_uploader(tt("file_uploader"), key=f"upl_{state_key}")

        st.write(tt("pdf_translate_title"))
        page_lang = st.session_state.get("lang", "ko")
        target_lang = get_papago_target_lang(page_lang)

        # 타겟 언어명, 페이지 언어에 맞춰 가져오기
        lang_display = get_display_lang_name(target_lang, page_lang)

        if uploaded:
            if uploaded.name.lower().endswith(".pdf"):
                if st.button(tt("btn_pdf_translate", lang_display), key=f"btn_translate_{state_key}_pdf"):
                    pdf_bytes = uploaded.read()
                    request_id = translate_pdf_with_papago(pdf_bytes, uploaded.name, target_lang)
                    if request_id:
                        with st.spinner(tt("pdf_translate_inprogress", lang_display)):
                            for _ in range(60):
                                status = check_translation_status(request_id)
                                if status == "COMPLETE" and request_id:
                                    pdf_data = download_translated_pdf(request_id)
                                    st.success(tt("pdf_translate_success", lang_display))
                                    st.download_button(
                                        label=tt("pdf_download_button", lang_display),
                                        data=pdf_data,
                                        file_name=f"translated_{target_lang}_{uploaded.name}",
                                        mime="application/pdf"
                                    )
                                    break
                                elif status == "failed":
                                    st.error(tt("pdf_translate_fail"))
                                    break
                                time.sleep(2)
                            else:
                                st.error(tt("pdf_translate_slow"))
                    else:
                        st.error(tt("pdf_translate_req_fail"))


        if uploaded and st.button(tt("upload_confirm_btn"), key=f"btn_{state_key}_upl"):
            st.success(tt("file_uploaded").format(uploaded.name))
            st.session_state[f"{state_key}_step2"] = True
            st.session_state[f"{state_key}_text"] = extract_text_from_file(uploaded)
    with st.expander(tt("text_confirm")):
        text = st.session_state.get(f"{state_key}_text", "")
        corrected = st.text_area(tt("extracted_text"), text, key=f"txt_{state_key}", height=200)
        if st.button(tt("text_edit_done_btn"), key=f"btn_{state_key}_corr"):
            st.session_state[f"{state_key}_step3"] = True
            st.session_state[f"{state_key}_text"] = corrected

    with st.expander(tt("analysis_results")):
        if st.session_state.get(f"{state_key}_step3"):
            text = st.session_state[f"{state_key}_text"]
            cat, summary1, kws, clauses = analyze_contract(text)
            summary = summarize_text_perplexity(text)
            lang = st.session_state.get("lang", "ko")
            if lang == "ko":
                trans_summary = summary
                trans_labels = [kw for kw in kws if kw in clauses] if kws else list(clauses.keys())
                trans_clauses = {}
                for lbl in trans_labels:
                    trans_clauses[lbl] = clauses[lbl]
            else:
                trans_summary = papago_translate(summary, lang)
                trans_labels = []
                trans_clauses = {}
                if kws:
                    for kw in kws:
                        if kw in clauses:
                            kw_trans = papago_translate(kw, lang)
                            trans_labels.append(kw_trans)
                            trans_clauses[kw_trans] = [papago_translate(s, lang) for s in clauses[kw]]
                else:
                    for term in clauses.keys():
                        kw_trans = papago_translate(term, lang)
                        trans_labels.append(kw_trans)
                        trans_clauses[kw_trans] = [papago_translate(s, lang) for s in clauses[term]]
            st.markdown(tt("summary_result"))
            st.write(trans_summary)
            st.markdown(tt("risk_keywords"))
            # ─── 위험 조항 비율 계산 및 표시 ───
            sents_full = re.split(r'(?<=[.?!])\s+', text)
            total_sentences = len([s for s in sents_full if s.strip()])
            matched_sentences = sum(len(v) for v in clauses.values())
            percent = (matched_sentences / total_sentences * 100) if total_sentences else 0.0
            pct_str = f"{percent:.1f}%"

            # 메시지 결정
            if percent < 10:
                msg = "위험조항이 일부 검출되었으니 계약서를 다시 검토해 주세요."
                color = "green"
            elif percent < 30:
                msg = "위험조항이 다소 검출되었으니, 계약 내용을 재확인해 주세요."
                color = "orange"
            elif percent < 50:
                msg = "다량의 위험조항이 발견되었습니다. 계약을 권고하지 않습니다."
                color = "red"
            else:
                msg = "계약서 대부분이 위험조항으로 검출되었습니다."
                color = "darkred"

            st.markdown(
                f"""
                <div style="display:flex; align-items:center; margin-bottom:8px;">
                <div style="font-size:2rem; font-weight:bold; margin-right:16px;">{pct_str}</div>
                <div style="color:{color}; font-size:1rem;">{msg}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

            st.progress(min(percent / 100, 1.0))
            if not clauses:
                st.write(tt("no_risk_keywords"))
            else:
                st.write(", ".join(trans_labels))
                st.markdown(tt("problem_clause_detail"))
                for lbl in trans_labels:
                    st.markdown(f"- **{lbl}**")
                    for s in trans_clauses[lbl]:
                        st.write(f"    - {s}")
            st.markdown(tt("original_text"))
            st.text_area(tt("original_text_area"), text, height=200)
            st.session_state[f"{state_key}_step4"] = True
        else:
            st.info(tt("step3_incomplete"))

with st.expander(tt("standard_dictionary_expander"), expanded=True):
    stdict_key = "F45E2E800C4B7B046E49DA0F67CF62C2"
    oms_key    = "DE3B11451FB95035936EA6519CC102E1"

    word = st.text_input(tt("search_word_input"), key="stdict_oms_input")
    search_btn = st.button(tt("search_both_btn"), key="btn_dicts_dual_search")

    stdict_res, oms_res = None, None

    if search_btn and word.strip():
        try:
            res1 = requests.get(
                "https://stdict.korean.go.kr/api/search.do",
                params={
                    "certkey_no": "7828",
                    "key": stdict_key,
                    "type_search": "search",
                    "req_type": "json",
                    "q": word
                },
                timeout=7
            )
            stdict_status = res1.status_code
            stdict_res = []
            if stdict_status == 200:
                try:
                    data = res1.json()
                    stdict_res = data.get("channel", {}).get("item", [])
                except Exception:
                    stdict_res = "PARSING_ERR"
            else:
                stdict_res = "HTTP_ERR"
        except Exception:
            stdict_res = "EXCEPTION"
        try:
            res2 = requests.get(
                "https://opendict.korean.go.kr/api/search",
                params={
                    "key": oms_key,
                    "target_type": "search",
                    "req_type": "json",
                    "part": "word",
                    "q": word,
                    "sort": "dict",
                    "start": 1,
                    "num": 10
                },
                timeout=7
            )
            oms_status = res2.status_code
            oms_res = []
            if oms_status == 200:
                try:
                    data = res2.json()
                    oms_res = data.get("channel", {}).get("item", [])
                except Exception:
                    oms_res = "PARSING_ERR"
            else:
                oms_res = "HTTP_ERR"
        except Exception:
            oms_res = "EXCEPTION"

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(tt("standard_dictionary_title"))
        if search_btn:
            if not word.strip():
                st.info(tt("search_word_warning"))
            elif stdict_res in ("HTTP_ERR", "PARSING_ERR", "EXCEPTION"):
                st.error(tt("dict_response_error"))
            elif not stdict_res:
                st.warning(tt("no_search_result"))
            else:
                for entry in stdict_res:
                    word_ = entry.get("word", "")
                    pos = entry.get("pos", "")
                    sense = entry.get("sense", {})
                    definition = sense.get("definition", "") if isinstance(sense, dict) else ""
                    st.markdown(f"**{word_}** ({pos})")
                    st.write(f"- {definition}")
                st.caption(tt("dictionary_source_caption_std"))

    with col2:
        st.markdown(tt("woorimal_dictionary_title"))
        if search_btn:
            if not word.strip():
                st.info(tt("search_word_warning"))
            elif oms_res in ("HTTP_ERR", "PARSING_ERR", "EXCEPTION"):
                st.error(tt("dict_response_error"))
            elif not oms_res:
                st.warning(tt("no_search_result"))
            else:
                for entry in oms_res:
                    word_ = entry.get("word", "")
                    senses = entry.get("sense", [])
                    st.markdown(f"**{word_}**")
                    for sense in senses:
                        definition = sense.get("definition", "")
                        cat = sense.get("cat", "")
                        st.write(f"- ({cat}) {definition}")
                st.caption(tt("dictionary_source_caption_oms"))

with st.expander(tt('translation'), expanded=False):
    my_text = st.text_area('번역할 텍스트 입력 (Enter text to translate)', key='mymemory_text')
    if st.button('번역 (MyMemory)', key='btn_mymemory'):
        if not my_text:
            st.error('번역할 텍스트를 입력하세요. (Please enter text to translate)')
        else:
            mm_url = 'https://api.mymemory.translated.net/get'
            params = {'q': my_text, 'langpair': 'ko|en'}
            resp = requests.get(mm_url, params=params)
            if resp.status_code != 200:
                st.error(f'번역 실패: {resp.status_code} (Translation failed)')
                st.write(resp.text)
            else:
                data = resp.json()
                translated = data.get('responseData', {}).get('translatedText', '')
                st.markdown('**번역 결과 (Translation Result)**')
                st.write(translated)
                st.caption('출처: MyMemory Translated API')
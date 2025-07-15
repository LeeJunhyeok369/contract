import torch, pickle
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
MODEL_DIR = "./my_contract_model"
# MODEL_DIR = r"C:/Users/PC/Desktop/새 폴더/my_contract_model"

# 디바이스 설정
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# 모델 및 토크나이저 로드
tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR).to(device)

# 라벨 인코더 로드
with open(f"{MODEL_DIR}/label_encoder.pkl", "rb") as f:
    le = pickle.load(f)

# 요약 파이프라인 (CPU 강제)
summarizer = pipeline(
    "summarization",
    model="facebook/bart-large-cnn",
    device=-1
)

def predict(text):
    try:
        if not text.strip():
            return "⚠️ 입력이 비어 있습니다."
        
        # 토큰화 및 디바이스 이동
        inputs = tokenizer(
            text, return_tensors="pt",
            truncation=True, padding="max_length", max_length=128
        ).to(device)
        
        with torch.no_grad():
            outputs = model(**inputs)
            pred = torch.argmax(outputs.logits, dim=1).item()
            label = le.inverse_transform([pred])[0]
            return label
        
    except Exception as e:
        return f"⚠️ 분류 중 오류 발생: {e}"

def summarize(text):
    try:
        text = text.strip()
        if not text:
            return "⚠️ 입력이 비어 있습니다."
        
        # 길이 제한 (대략 700단어로 자름)
        if len(text.split()) > 700:
            text = ' '.join(text.split()[:700])
        
        result = summarizer(
            text, max_length=130, min_length=30, do_sample=False
        )[0]['summary_text']
        return result
        
    except Exception as e:
        return f"⚠️ 요약 중 오류 발생: {e}"

from __future__ import annotations
from pathlib import Path
from pypdf import PdfReader

def extract_pdf_text(path: Path) -> str:
    reader=PdfReader(str(path)); return "\n\n".join((p.extract_text() or "") for p in reader.pages).strip()

def run_ocr(path: Path) -> dict:
    if path.suffix.lower()==".pdf":
        text=extract_pdf_text(path)
        if len(text)>30: return {"text":text,"boxes":[],"engine":"PDF原始文字提取","local":True}
    try:
        from paddleocr import PaddleOCR
        ocr=PaddleOCR(lang="ch",use_doc_orientation_classify=False,use_doc_unwarping=False,use_textline_orientation=False)
        result=ocr.predict(str(path)); texts=[]; boxes=[]
        for page in result:
            data=page.json if hasattr(page,"json") else page
            data=data.get("res",data) if isinstance(data,dict) else {}
            rec_texts=data.get("rec_texts",[]); rec_scores=data.get("rec_scores",[]); rec_polys=data.get("rec_polys",[])
            for i,t in enumerate(rec_texts):
                texts.append(t); boxes.append({"text":t,"confidence":float(rec_scores[i]) if i<len(rec_scores) else None,"polygon":rec_polys[i].tolist() if i<len(rec_polys) and hasattr(rec_polys[i],"tolist") else []})
        return {"text":"\n".join(texts),"boxes":boxes,"engine":"PaddleOCR CPU","local":True}
    except ImportError:
        raise RuntimeError("PaddleOCR 尚未安装，请运行 setup.bat 的 OCR 安装步骤")


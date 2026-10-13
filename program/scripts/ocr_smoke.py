from __future__ import annotations
from pathlib import Path
import os
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[2];out=Path(os.getenv("CKH_OCR_TEST_DIR",ROOT/"runtime"/"cache"))/"ocr_test.png";out.parent.mkdir(parents=True,exist_ok=True)
if not (os.getenv("CKH_OCR_REUSE")=="1" and out.exists()):
    im=Image.new("RGB",(640,140),"white");d=ImageDraw.Draw(im);font_path=Path("C:/Windows/Fonts/msyh.ttc");font=ImageFont.truetype(str(font_path),34) if font_path.exists() else ImageFont.load_default();d.text((20,40),"Communication 2028  信号与系统",fill="black",font=font);im.save(out)
from app.ocr import run_ocr
r=run_ocr(out);print("OCR smoke:",r["engine"],len(r["text"]),r["text"]);assert "2028" in r["text"]

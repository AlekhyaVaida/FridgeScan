# scripts/detection/run_ocr.py
import easyocr

reader = easyocr.Reader(['en'], gpu=False)

def run_ocr(image_path):
    result = reader.readtext(image_path)
    if not result:
        return None
    text = ' '.join([r[1] for r in result])
    return text.lower()

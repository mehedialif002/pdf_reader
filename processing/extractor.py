import fitz   
import re
import os

class DocumentExtractor:

    def extract(self, file_path: str) -> dict:
        doc   = fitz.open(file_path)
        pages = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")

            
            if len(text.strip()) < 30:
                text = self._ocr_page(page)

            cleaned = self._clean_text(text)
            pages.append({
                "page"    : page_num + 1,
                "text"    : cleaned,
                "length"  : len(cleaned),
                "has_text": len(cleaned) > 20
            })

        total_pages = len(doc)
        doc.close()

        full_text  = "\n\n".join([
            f"[Page {p['page']}]\n{p['text']}"
            for p in pages if p["has_text"]
        ])

        return {
            "file"        : os.path.basename(file_path),
            "total_pages" : total_pages,
            "total_chars" : sum(p["length"] for p in pages),
            "pages"       : pages,
            "full_text"   : full_text,
            "structured"  : self._extract_structured_fields(full_text),
            "quality"     : "good" if sum(p["length"] for p in pages) > 500 else "partial"
        }

    def _ocr_page(self, page) -> str:
        try:
            import pytesseract
            from PIL import Image
            import io
            pix  = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img  = Image.open(io.BytesIO(pix.tobytes("png")))
            return pytesseract.image_to_string(img)
        except:
            blocks = page.get_text("blocks")
            return " ".join([b[4] for b in blocks if b[4].strip()])

    def _clean_text(self, text: str) -> str:
        if not text:
            return ""
        text = re.sub(r" {2,}", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _extract_structured_fields(self, text: str) -> dict:
        fields = {"dates": [], "amounts": [], "case_numbers": [], "key_terms": []}

        
        fields["dates"] = re.findall(
            r"\b(?:January|February|March|April|May|June|July|August|"
            r"September|October|November|December)\s+\d{1,2},?\s+\d{4}\b",
            text, re.IGNORECASE
        )[:5]

        
        fields["amounts"] = re.findall(r"\$[\d,]+(?:\.\d{2})?", text)[:5]

        
        fields["case_numbers"] = re.findall(
            r"\bCase\s+No\.?\s*[\w/-]+\b", text, re.IGNORECASE
        )[:3]

        
        terms = ["plaintiff","defendant","agreement","breach","damages","contract"]
        fields["key_terms"] = [t for t in terms if t in text.lower()]

        return fields
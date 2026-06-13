import fitz  # PyMuPDF
import io
import json
import numpy as np
import easyocr
from PIL import Image
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.services.llm_factory import LLMFactory
import torch

# --- Global Caching for OCR ---
# This ensures the heavy EasyOCR model is loaded only ONCE per application run,
# not every time a user uploads a file.
_SHARED_OCR_READER = None

def get_ocr_reader():
    global _SHARED_OCR_READER
    if _SHARED_OCR_READER is None:
        print("Initializing EasyOCR Model... (This happens only once)")
        # Set gpu=True if you have a compatible CUDA device
        _SHARED_OCR_READER = easyocr.Reader(['en'], gpu=torch.cuda.is_available())
    return _SHARED_OCR_READER

class JDAnalyzer:
    def __init__(self):
        self.llm = LLMFactory.get_ollama_tool()
        # Note: We no longer initialize self.reader here to prevent bottlenecks.

    def extract_text_from_pdf(self, pdf_path):
        """Extracts text from PDF using OCR (EasyOCR) only if necessary."""
        all_text = ""
        try:
            doc = fitz.open(pdf_path)
            for i in range(doc.page_count):
                page = doc.load_page(i)
                
                # 1. Attempt fast direct text extraction first
                try:
                    page_text = page.get_text("text") or ""
                except Exception:
                    try:
                        page_text = page.get_text() or ""
                    except Exception:
                        page_text = ""

                # 2. If text exists, use it. If not, Fallback to OCR.
                if page_text and page_text.strip():
                    all_text += page_text.strip() + "\n\n"
                else:
                    # ONLY load the OCR reader if we actually hit an image-only page
                    print(f"Page {i+1} appears to be an image. Running OCR...")
                    reader = get_ocr_reader()
                    
                    pix = page.get_pixmap(dpi=300)
                    img_bytes = pix.tobytes("png")
                    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                    img_arr = np.array(img)
                    
                    # detail=0 returns strings; paragraph=True attempts to merge lines
                    results = reader.readtext(img_arr, detail=0, paragraph=True)
                    page_text = "\n".join(results) if results else ""
                    
                    if page_text and page_text.strip():
                        all_text += page_text + "\n\n"
            doc.close()
        except Exception as e:
            print(f"Error processing PDF {pdf_path}: {e}")
            return None

        if not all_text or not all_text.strip():
            msg = "File is blank or unreadable"
            print(f"{msg}: {pdf_path}")
            return None

        return all_text

    def _invoke_chain(self, template, variables):
        """Helper to run a LangChain prompt."""
        prompt = PromptTemplate(
            input_variables=list(variables.keys()),
            template=template
        )
        chain = prompt | self.llm | StrOutputParser()
        return chain.invoke(variables).strip()

    def extract_skills(self, text, is_jd=False):
        """Extracts skills from Resume or JD text."""
        context_label = "Job Description" if is_jd else "Resume Text"
        prompt = f"""
        You are an expert HR assistant. Extract a comprehensive list of distinct technical and soft skills 
        from the following {{text_type}}. Present them as a comma-separated list. 
        Do not include any other text.
        
        {context_label}:
        {{text}}
        
        Skills:
        """
        return self._invoke_chain(prompt, {"text": text, "text_type": context_label})

    def get_comparison(self, resume_skills, jd_skills):
        """Returns common and missing skills as JSON objects."""
        
        common_prompt = """
        Given these lists:
        Resume Skills: {resume_skills}
        JD Skills: {jd_skills}
        
        Identify ONLY skills in BOTH lists.
        Return EXACTLY in this JSON format: {{ "common_skills": [...] }}
        """
        
        missing_prompt = """
        Given these lists:
        Resume Skills: {resume_skills}
        JD Skills: {jd_skills}
        
        Identify ONLY skills in JD but NOT in Resume.
        Return EXACTLY in this JSON format: {{ "skills_to_learn": [...] }}
        """

        common_raw = self._invoke_chain(common_prompt, {"resume_skills": resume_skills, "jd_skills": jd_skills})
        missing_raw = self._invoke_chain(missing_prompt, {"resume_skills": resume_skills, "jd_skills": jd_skills})
        
        return self._clean_json(common_raw), self._clean_json(missing_raw)

    def generate_interview_questions(self, common_skills_json_str):
        """Generates 10 interview questions based on common skills."""
        prompt = """
        You are an expert technical interviewer.
        Given this JSON of common skills: {common_json}
        
        Generate exactly 10 practical, non-generic interview questions.
        Return ONLY JSON: {{ "questions": ["q1", "q2", ...] }}
        """
        raw = self._invoke_chain(prompt, {"common_json": str(common_skills_json_str)})
        return self._clean_json(raw)

    def _clean_json(self, raw_str):
        """Cleans LLM output to valid dict."""
        cleaned = raw_str.strip().strip("'").strip('"').replace("\\'", "'")
        # Attempt to find JSON block if wrapped in markdown
        if "```json" in cleaned:
            import re
            match = re.search(r'```json\s*(\{.*?\})\s*```', cleaned, re.DOTALL)
            if match: cleaned = match.group(1)
            
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            print(f"JSON Parse Error: {cleaned}")
            return None
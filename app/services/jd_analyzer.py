import fitz  # PyMuPDF
import io
import json
import re
import numpy as np
import easyocr
import torch

from PIL import Image
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.services.llm_factory import LLMFactory


# -----------------------------
# Global OCR Cache
# -----------------------------

_SHARED_OCR_READER = None


def get_ocr_reader():
    """
    Loads EasyOCR only once during application runtime.
    """
    global _SHARED_OCR_READER

    if _SHARED_OCR_READER is None:
        print("Initializing EasyOCR model...")

        _SHARED_OCR_READER = easyocr.Reader(
            ["en"],
            gpu=torch.cuda.is_available()
        )

    return _SHARED_OCR_READER


# -----------------------------
# JD Analyzer Class
# -----------------------------

class JDAnalyzer:

    def __init__(self):
        """
        Initialize local Ollama model.
        """
        self.llm = LLMFactory.get_ollama_tool()


    def extract_text_from_pdf(self, pdf_path):
        """
        Extract text from PDF.
        Uses direct extraction first.
        Falls back to OCR for image PDFs.
        """

        all_text = ""

        try:
            document = fitz.open(pdf_path)

            for page_number in range(document.page_count):

                page = document.load_page(page_number)

                try:
                    text = page.get_text("text")

                except Exception:
                    text = ""

                if text and text.strip():

                    all_text += text.strip() + "\n\n"

                else:

                    print(
                        f"Page {page_number + 1} has no text. Running OCR..."
                    )

                    reader = get_ocr_reader()

                    pix = page.get_pixmap(dpi=150)

                    image = Image.open(
                        io.BytesIO(
                            pix.tobytes("png")
                        )
                    ).convert("RGB")

                    image_array = np.array(image)

                    results = reader.readtext(
                        image_array,
                        detail=0,
                        paragraph=True
                    )

                    extracted_text = "\n".join(results)

                    all_text += extracted_text + "\n\n"

            document.close()


        except Exception as error:

            print(
                f"PDF extraction failed: {error}"
            )

            return None


        if not all_text.strip():

            print("No readable text found in PDF.")

            return None


        return all_text


    def _invoke_chain(self, template, variables):
        """
        Send request to Ollama.
        Trims very large text for faster processing.
        """

        if "text" in variables:

            size = len(
                variables["text"]
            )

            if size > 1500:

                print(
                    f"Reducing text from {size} characters to 1500 characters."
                )

                variables["text"] = variables["text"][:1500]


        print("Sending request to Ollama...")


        prompt = PromptTemplate(
            input_variables=list(variables.keys()),
            template=template
        )


        chain = (
            prompt
            | self.llm
            | StrOutputParser()
        )


        try:

            response = chain.invoke(
                variables
            )

            print(
                "Ollama response received successfully."
            )

            return response.strip()


        except Exception as error:

            print(
                f"Ollama invocation failed: {error}"
            )

            return ""


    def extract_skills(self, text, is_jd=False):
        """
        Extract skills using keyword matching.
        """

        skills_database = [
            "Python",
            "Java",
            "C++",
            "JavaScript",
            "HTML",
            "CSS",
            "React",
            "Node.js",
            "Flask",
            "Django",
            "SQL",
            "MySQL",
            "MongoDB",
            "Machine Learning",
            "Deep Learning",
            "AI",
            "Data Analysis",
            "Git",
            "GitHub",
            "Docker",
            "AWS",
            "REST API",
            "Problem Solving",
            "Communication",
            "Leadership",
            "OOP",
            "DSA"
        ]

        found_skills = []

        lower_text = text.lower()

        for skill in skills_database:
            if skill.lower() in lower_text:
                found_skills.append(skill)

        result = ", ".join(found_skills)

        print("Extracted skills:", result)

        return result


    def get_comparison(self, resume_skills, jd_skills):
        """
        Compare Resume and JD skills.
        Uses Python matching instead of LLM for accuracy.
        """

        print("Comparing skills using Python matching...")


        def normalize(skills):
            return {
                skill.strip().lower()
                for skill in skills.split(",")
                if skill.strip()
            }


        resume_set = normalize(resume_skills)
        jd_set = normalize(jd_skills)


        common = sorted(
            resume_set.intersection(jd_set)
        )

        missing = sorted(
            jd_set.difference(resume_set)
        )


        result_common = {
            "common_skills": [
                skill.title()
                for skill in common
            ]
        }


        result_missing = {
            "skills_to_learn": [
                skill.title()
                for skill in missing
            ]
        }


        print(
            "Matched skills:",
            result_common
        )

        print(
            "Missing skills:",
            result_missing
        )


        return (
            result_common,
            result_missing
        )


    def generate_interview_questions(self, common_skills_json):
        """
        Generate interview questions in strict JSON format.
        """

        prompt = """
        You are a JSON API.

        STRICT RULES:
        1. Return ONLY valid JSON.
        2. Do not write explanations.
        3. Do not write Python code.
        4. Do not use markdown.
        5. Your response must start with { and end with }.
        6. Generate exactly 5 practical technical interview questions.

        Skills:
        {common_json}

        Return exactly in this format:

        {{
            "questions": [
                "Question 1",
                "Question 2",
                "Question 3",
                "Question 4",
                "Question 5"
            ]
        }}
        """

        print("Generating interview questions...")


        response = self._invoke_chain(
            prompt,
            {
                "common_json": str(common_skills_json)
            }
        )


        print(
            "Raw question response:",
            response
        )


        return self._clean_json(response)


    def _clean_json(self, raw_text):
        """
        Cleans and converts Ollama JSON response into Python dictionary.
        Provides fallback questions if JSON parsing fails.
        """

        if not raw_text:
            print("Empty response received from Ollama. Using fallback questions.")

            return {
                "questions": [
                    "Explain your strongest programming language.",
                    "Describe a challenging project you have worked on.",
                    "What are the core concepts of object-oriented programming?",
                    "How do you debug and optimize your code?",
                    "Explain a technical problem you solved recently."
                ]
            }

        cleaned = (
            raw_text
            .strip()
            .strip("'")
            .strip('"')
            .replace("\\'", "'")
        )

        # Handle markdown JSON blocks from LLM
        if "```json" in cleaned:

            match = re.search(
                r"```json\s*(\{.*?\})\s*```",
                cleaned,
                re.DOTALL
            )

            if match:
                cleaned = match.group(1)

        # Try normal JSON parsing
        try:
            return json.loads(cleaned)

        except json.JSONDecodeError as error:

            print(
                f"JSON parsing failed: {error}"
            )

            print(
                "Invalid JSON received from Ollama:"
            )

            print(cleaned)

            print(
                "Using fallback interview questions."
            )

            return {
                "questions": [
                    "Explain your experience with the technologies used in your projects.",
                    "Describe a difficult technical issue you faced and how you solved it.",
                    "What programming concepts do you use most frequently?",
                    "How would you improve the performance of an application?",
                    "What coding best practices do you follow?"
                ]
            }
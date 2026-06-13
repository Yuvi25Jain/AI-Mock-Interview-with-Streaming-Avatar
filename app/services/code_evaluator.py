import json
import re
import logging
from langchain_core.messages import SystemMessage, HumanMessage
from app.services.llm_factory import LLMFactory
from app.db import get_db

class CodeEvaluator:
    def __init__(self):
        self.model_name = "gemini"
        try:
            self.model = LLMFactory.get_google_chat()
            logging.info("Using Gemini for code evaluation.")
        except Exception as e:
            logging.warning(f"Gemini failed at init ({e}), falling back to Ollama for code evaluation.")
            self.model = LLMFactory.get_ollama_chat()
            self.model_name = "ollama"

    def _invoke(self, messages):
        """Invoke the current model, fallback to Ollama if Gemini fails at runtime."""
        if self.model_name == "gemini":
            try:
                response = self.model.invoke(messages)
                return response
            except Exception as e:
                logging.warning(f"Gemini failed at invoke: {e}. Falling back to Ollama for this and future calls.")
                self.model = LLMFactory.get_ollama_chat()
                self.model_name = "ollama"
                return self.model.invoke(messages)
        else:
            return self.model.invoke(messages)

    def evaluate(self, code, language, question, user_id=None, filename=None):
        """Analyzes code and saves result to DB."""
        prompt = f"""
        You are an Expert Code Evaluator.
        Question: {question}
        Language: {language}
        Code:
        ```{language}
        {code}
        ```
        
        Analyze for syntax, logic, correctness, and proper indentation (critical for languages like Python)
        Return ONLY this JSON format:
        {{
            "passed": true/false,
            "score": "X/Y",
            "feedback": "detailed feedback",
            "test_results": [
                {{ "test_case": 1, "input": "...", "expected": "...", "predicted_output": "...", "passed": true/false }}
            ]
        }}
        """
        try:
            response = self._invoke([HumanMessage(content=prompt)])
            result = self._parse_response(response.content if hasattr(response, 'content') else response)
            self._save_to_db(user_id, filename, language, question, code, result)
            return result
        except Exception as e:
            return {"passed": False, "score": "0/0", "feedback": str(e)}

    def get_hint(self, prompt):
        from langchain_core.messages import SystemMessage, HumanMessage
        
        system_prompt = "You are a helpful coding assistant. Provide concise, accurate hints for the given question without giving away the full solution. Only give 1 language agnostic hint. Do not include any other text before or after."
        
        try:
            response = self._invoke([SystemMessage(content=system_prompt), HumanMessage(content=prompt)])
        except Exception as e:
            import logging
            logging.warning(f"Gemini failed at invoke: {e}. Falling back to Ollama.")
            fallback_model = LLMFactory.get_ollama_chat()
            response = fallback_model.invoke([SystemMessage(content=system_prompt), HumanMessage(content=prompt)])
        
        if hasattr(response, 'content'):
            return response.content
        return response

    def _parse_response(self, text):
        """Extracts JSON from response."""
        try:
            text = text.strip()
            # Remove markdown if present
            if "```" in text:
                match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', text, re.DOTALL)
                if match: text = match.group(1)
            return json.loads(text)
        except:
            return {"passed": False, "feedback": text, "score": "0/0"}

    def _save_to_db(self, user_id, filename, language, question, code, result):
        try:
            db = get_db()
            status = str(result.get('passed', False))
            result_json = json.dumps(result)
            db.execute("""
                INSERT INTO code_checks (user_id, filename, language, question_context, code, result_json, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, filename, language, question, code, result_json, status))
            db.commit()
        except Exception as e:
            print(f"DB Save Error: {e}")
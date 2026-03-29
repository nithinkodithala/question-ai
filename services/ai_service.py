import google.generativeai as genai
import os
import logging
import re
from dotenv import load_dotenv
import json
from typing import Optional, AsyncGenerator

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Configure GenAI
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
else:
    logger.warning("GEMINI_API_KEY not found in environment variables.")

DEFAULT_MODEL = "gemini-2.0-flash"

async def generate_questions_stream_with_gemini(
    document_text: str,
    topic: str,
    difficulty: str,
    question_types: list[str],
    number_of_questions: int,
    custom_structure: Optional[str] = None,
    total_marks: int = 40,
    language: str = "English"
):
    """Stream questions using Gemini AI."""
    if not api_key or api_key == "YOUR_GEMINI_API_KEY_HERE":
        yield "ERROR: Gemini API key is missing or invalid. Please configure it in the .env file."
        return

    structure_inst = f"\nCustom Structure Instructions: {custom_structure}" if custom_structure else ""
    
    marks_specific_rules = ""
    if total_marks == 40:
        marks_specific_rules = """
STRICT STRUCTURE FOR 40 MARKS PAPER:
1. Section A (Questions 1 to 10):
   (Section-A consists of 10 questions 1 mark each)
   - MCQ ONLY. Options A, B, C, D MUST be on a SINGLE line underneath each question.
2. Section B (Questions 11 to 14):
   (Section-B consists of 4 questions 2 marks each)
3. Section C (Questions 15 to 17):
   (Section-C consists of 3 questions 3 marks each)
4. Section D (Question 18):
   (Section-D consists of 1 question 5 marks each)
5. Section E (Questions 19 and 20):
   (Case study questions)
"""
    elif total_marks == 80:
        marks_specific_rules = """
STRICT STRUCTURE FOR 80 MARKS PAPER:
1. Section A (Questions 1 to 20):
   (Section-A consists of 20 questions 1 mark each)
   - MCQ ONLY. All options A, B, C, D on a SINGLE line beneath the question.
2. Sections B-E: Using the 80M distribution with appropriate Section descriptions.
"""

    topics_to_use = custom_structure if custom_structure else topic

    system_instr = f"""You are a professional Question Paper Generator for Indian school exams (CBSE/State Board).

RULES FOR 40 MARKS PERIODIC TEST PAPER:
1. Generate EXACTLY 20 questions total.
2. SECTION A — MULTIPLE CHOICE QUESTIONS (Questions 1 to 10):
   - EVERY question MUST be a Multiple Choice Question (MCQ).
   - EVERY question MUST have EXACTLY 4 options: A, B, C, D.
   - Options for each question must appear on a SINGLE LINE immediately after the question.
   - Example:
     1. Which of the following is an irrational number?
     A. 4/5   B. √2   C. 0.25   D. 1/3
     2. The degree of a linear polynomial is:
     A. 0   B. 1   C. 2   D. 3
3. SECTION B — Questions 11 to 14 (Very Short Answer, 2 marks each).
4. SECTION C — Questions 15 to 17 (Short Answer, 3 marks each).
5. SECTION D — Question 18 (Long Answer, 5 marks).
6. SECTION E — Questions 19 and 20 (Case-based, 4 marks each).

RULES FOR 80 MARKS PAPER:
1. Section A: 20 MCQs (same format as above).
2. Sections B-E: As per 80M distribution.

STRICT RULES (ALL PAPERS):
- Do NOT add marks like (1), (2), (1 mark) after each question.
- Use PLAIN TEXT ONLY — no bold, no italics, no bullet symbols.
- Do NOT include a title/header at the top.
- Generate questions ONLY from these chapters/topics: {topics_to_use}
- Ignore publisher info, copyright notices, or non-educational metadata.
- Language: {language}
"""

    prompt = f"""Source material for question generation:
{document_text}

TASK: Generate a {total_marks}-mark question paper covering ONLY these topics: {topics_to_use}

{marks_specific_rules}

REMINDER:
- Section A questions (1-10) are MCQs. Each MUST have: 
  A. [option]   B. [option]   C. [option]   D. [option]
  on the line right below the question text.
- No individual marks per question.
- Start directly with SECTION A.
"""
    # Section descriptions injected by code for 40M papers
    SECTION_DESCRIPTIONS_40M = {
        "SECTION A": "(Section-A consists of 10 questions 1 mark each)",
        "SECTION B": "(Section-B consists of 4 questions 2 marks each)",
        "SECTION C": "(Section-C consists of 3 questions 3 marks each)",
        "SECTION D": "(Section-D consists of 1 question 5 marks each)",
        "SECTION E": "(Case study questions)",
    }

    try:
        model = genai.GenerativeModel(
            model_name=DEFAULT_MODEL,
            system_instruction=system_instr
        )
        response = await model.generate_content_async(prompt, stream=True)
        
        # Collect full response for reliable post-processing
        full_text = ""
        async for chunk in response:
            full_text += chunk.text
        
        # Step 1: Remove markdown
        full_text = full_text.replace('**', '').replace('*', '').replace('#', '').replace('$', '')
        
        # Step 2: Strip ALL per-question marks anywhere in the line
        # Handles: (1 mark), (1 M), (1), (2 marks), even with trailing ? or spaces
        full_text = re.sub(r'\s*\(\s*\d+\s*(?:marks?|M|m)?\s*\)\s*\??', '', full_text)
        
        # Step 3: Convert inline options (a) text (b) text → A. text   B. text   C. text   D. text
        def convert_inline_options(text):
            lines = text.split('\n')
            result = []
            for line in lines:
                # Detect lines with inline (a)/(b)/(c)/(d) options
                if re.search(r'\(a\)', line, re.IGNORECASE) and re.search(r'\(b\)', line, re.IGNORECASE):
                    # Extract question text before first (a)
                    q_match = re.match(r'^(.*?)\s*\(a\)(.*?)\(b\)(.*?)\(c\)(.*?)\(d\)(.*?)$', line, re.IGNORECASE)
                    if q_match:
                        q_text = q_match.group(1).strip()
                        opt_a = q_match.group(2).strip()
                        opt_b = q_match.group(3).strip()
                        opt_c = q_match.group(4).strip()
                        opt_d = q_match.group(5).strip()
                        result.append(q_text)
                        result.append(f"A. {opt_a}   B. {opt_b}   C. {opt_c}   D. {opt_d}")
                        continue
                result.append(line)
            return '\n'.join(result)
        
        full_text = convert_inline_options(full_text)
        
        # Step 4: For 40M, inject section descriptions after section headers (guaranteed by code)
        if total_marks == 40:
            lines = full_text.split('\n')
            new_lines = []
            for i, line in enumerate(lines):
                new_lines.append(line)
                stripped = line.strip()
                for sec_key, description in SECTION_DESCRIPTIONS_40M.items():
                    if re.match(rf'^{sec_key}\b', stripped, re.IGNORECASE):
                        next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
                        if description not in next_line:
                            new_lines.append(description)
                        break
            full_text = '\n'.join(new_lines)
        
        yield full_text
            
    except Exception as e:
        yield f"Error: {str(e)}"


async def generate_answer_key_with_gemini(
    document_text: str,
    question_paper_text: str,
    language: str = "English"
) -> str:
    """Generate an answer key for a previously generated question paper."""
    
    prompt = f"""Based on the following document context:
{document_text}

Generate a formal answer key for this question paper:
{question_paper_text}

Instructions:
1. Provide correct and detailed answers for each question.
2. Use {language} for all answer text and content.
3. DO NOT use any markdown symbols like **, *, #, $.
4. Maintain same numbering as the question paper.
5. Provide ONLY the answer key text.
"""

    try:
        model = genai.GenerativeModel(DEFAULT_MODEL)
        response = await model.generate_content_async(prompt)
        clean_text = response.text.replace('**', '').replace('*', '').replace('#', '').replace('$', '')
        return clean_text
    except Exception as e:
        return f"Error occurred while generating Answer Key: {str(e)}"

async def analyze_document_metadata(text: str) -> dict:
    """Analyze text to guess Subject and Class/Grade."""
    prompt = f"""Analyze the the following educational content and identify the the Subject and Grade level.
    Return ONLY a JSON object with keys "subject" and "class".
    Example: {{"subject": "Biology", "class": "Grade 10"}}
    
    Content:
    {text[:5000]}
    """
    try:
        model = genai.GenerativeModel(DEFAULT_MODEL)
        response = await model.generate_content_async(prompt)
        # Find JSON in response
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except:
        pass
    return {"subject": "Unknown", "class": "Unknown"}

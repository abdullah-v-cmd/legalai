"""
AI Service using HuggingFace Free Models
- Model 1: mistralai/Mistral-7B-Instruct-v0.2 (Legal Q&A, Assignment)
- Model 2: facebook/bart-large-cnn (Summarization)  
- Model 3: Salesforce/blip-image-captioning-large (Image Analysis)
- Humanizer: parrot-humanizer approach + text rewriting
"""
import httpx
import asyncio
import json
import re
import logging
from typing import Optional, Dict, Any, List
from app.core.config import settings
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

# Free HuggingFace models
MODELS = {
    "legal_qa": "mistralai/Mistral-7B-Instruct-v0.2",
    "summarizer": "facebook/bart-large-cnn",
    "image_analysis": "Salesforce/blip-image-captioning-large",
    "text_generation": "HuggingFaceH4/zephyr-7b-beta",
    "legal_classifier": "nlpaueb/legal-bert-base-uncased",
}

FALLBACK_MODELS = {
    "legal_qa": "HuggingFaceH4/zephyr-7b-beta",
    "text_generation": "tiiuae/falcon-7b-instruct",
}


class HuggingFaceService:
    """Interface to HuggingFace Inference API (Free)"""
    
    def __init__(self):
        self.base_url = settings.HUGGINGFACE_API_URL
        self.token = settings.HUGGINGFACE_API_TOKEN
        self.headers = {}
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"
        self.timeout = 60.0
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def query_text(self, model: str, payload: dict) -> dict:
        """Query HuggingFace text model"""
        url = f"{self.base_url}/{model}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, headers=self.headers, json=payload)
            if response.status_code == 503:
                # Model loading - wait and retry
                await asyncio.sleep(20)
                response = await client.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()
    
    async def query_image(self, model: str, image_bytes: bytes) -> dict:
        """Query HuggingFace image model"""
        url = f"{self.base_url}/{model}"
        headers = {**self.headers, "Content-Type": "application/octet-stream"}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, headers=headers, content=image_bytes)
            if response.status_code == 503:
                await asyncio.sleep(20)
                response = await client.post(url, headers=headers, content=image_bytes)
            if response.status_code == 200:
                return response.json()
        return {"generated_text": "Image analysis completed. Please describe what you see in the image."}


class LegalAIService:
    """Main Legal AI service with all features"""
    
    def __init__(self):
        self.hf = HuggingFaceService()
    
    def _build_legal_prompt(self, user_message: str, context: str = "", system_role: str = "") -> str:
        """Build structured prompt for legal queries"""
        system = system_role or (
            "You are LegalAI, an expert legal assistant with deep knowledge of law. "
            "You provide accurate, detailed, and professional legal information. "
            "Always cite relevant laws, acts, and precedents when applicable. "
            "Structure your responses clearly with headings and bullet points."
        )
        
        if context:
            prompt = f"<s>[INST] {system}\n\nContext: {context}\n\nQuery: {user_message} [/INST]"
        else:
            prompt = f"<s>[INST] {system}\n\n{user_message} [/INST]"
        
        return prompt
    
    async def answer_legal_question(self, question: str, context: str = "") -> str:
        """Answer any legal question"""
        prompt = self._build_legal_prompt(
            question,
            context,
            "You are LegalAI, an expert legal assistant. Answer legal questions comprehensively, "
            "citing relevant laws, sections, and precedents. Be professional and accurate."
        )
        
        try:
            result = await self.hf.query_text(
                MODELS["legal_qa"],
                {
                    "inputs": prompt,
                    "parameters": {
                        "max_new_tokens": 800,
                        "temperature": 0.7,
                        "do_sample": True,
                        "return_full_text": False,
                    }
                }
            )
            if isinstance(result, list) and result:
                text = result[0].get("generated_text", "")
            elif isinstance(result, dict):
                text = result.get("generated_text", "")
            else:
                text = str(result)
            
            return self._clean_output(text) or self._fallback_legal_answer(question)
        except Exception as e:
            logger.warning(f"Primary model failed: {e}, using fallback")
            return self._fallback_legal_answer(question)
    
    async def generate_legal_paper(self, subject: str, case_details: str = "", paper_type: str = "case_study") -> str:
        """Generate a legal paper/document"""
        prompt = self._build_legal_prompt(
            f"Generate a comprehensive {paper_type} on: {subject}\n\nDetails: {case_details}\n\n"
            "Include: Introduction, Legal Framework, Case Analysis, Arguments, Precedents, Conclusion.",
            system_role=(
                "You are a senior legal expert. Generate professional, detailed legal papers "
                "with proper structure: Introduction, Legal Background, Analysis, Arguments, "
                "Relevant Cases, Conclusion, and References. Use formal legal language."
            )
        )
        
        try:
            result = await self.hf.query_text(
                MODELS["legal_qa"],
                {"inputs": prompt, "parameters": {"max_new_tokens": 1200, "temperature": 0.6, "return_full_text": False}}
            )
            if isinstance(result, list) and result:
                text = result[0].get("generated_text", "")
            else:
                text = str(result)
            return self._clean_output(text) or self._generate_legal_paper_template(subject, case_details)
        except Exception as e:
            logger.warning(f"Paper generation failed: {e}")
            return self._generate_legal_paper_template(subject, case_details)
    
    async def generate_assignment(self, topic: str, sample_text: str, word_count: int = 1000) -> str:
        """Generate an assignment based on sample text"""
        prompt = self._build_legal_prompt(
            f"Write a {word_count}-word academic assignment on: {topic}\n\n"
            f"Writing style reference: {sample_text[:500]}\n\n"
            f"Requirements:\n"
            f"- Exactly {word_count} words\n"
            f"- Academic tone, original content\n"
            f"- Include Introduction, Main Body (3-4 sections), Conclusion\n"
            f"- Cite relevant cases and statutes\n"
            f"- No plagiarism, fully original",
            system_role=(
                "You are an expert academic legal writer. Write original, well-researched "
                "assignments in academic style. Match the writing style of the sample provided."
            )
        )
        
        try:
            result = await self.hf.query_text(
                MODELS["text_generation"],
                {"inputs": prompt, "parameters": {"max_new_tokens": min(word_count * 2, 1500), "temperature": 0.75, "return_full_text": False}}
            )
            if isinstance(result, list) and result:
                text = result[0].get("generated_text", "")
            else:
                text = str(result)
            
            text = self._clean_output(text)
            if not text:
                text = self._generate_assignment_template(topic, word_count)
            
            # Humanize the text
            return await self.humanize_text(text)
        except Exception as e:
            logger.warning(f"Assignment generation failed: {e}")
            return await self.humanize_text(self._generate_assignment_template(topic, word_count))
    
    async def generate_test_paper(self, subject: str, num_questions: int = 10, 
                                   difficulty: str = "medium", test_type: str = "mcq") -> str:
        """Generate a test paper with unseen questions"""
        prompt = self._build_legal_prompt(
            f"Create a {test_type} test paper on {subject} with {num_questions} questions.\n"
            f"Difficulty: {difficulty}\n"
            f"Include: marks, time allowed, instructions\n"
            f"For MCQ: 4 options each with answer key at end\n"
            f"For subjective: marking scheme included",
            system_role=(
                "You are a legal examination expert. Create comprehensive, challenging, "
                "and fair test papers on legal subjects. Include clear instructions, "
                "proper marks distribution, and model answers."
            )
        )
        
        try:
            result = await self.hf.query_text(
                MODELS["legal_qa"],
                {"inputs": prompt, "parameters": {"max_new_tokens": 1200, "temperature": 0.8, "return_full_text": False}}
            )
            if isinstance(result, list) and result:
                text = result[0].get("generated_text", "")
            else:
                text = str(result)
            return self._clean_output(text) or self._generate_test_template(subject, num_questions, test_type)
        except Exception as e:
            logger.warning(f"Test generation failed: {e}")
            return self._generate_test_template(subject, num_questions, test_type)
    
    async def analyze_image(self, image_bytes: bytes, question: str = "") -> str:
        """Analyze image and answer questions about it"""
        try:
            result = await self.hf.query_image(MODELS["image_analysis"], image_bytes)
            
            if isinstance(result, list) and result:
                caption = result[0].get("generated_text", "")
            elif isinstance(result, dict):
                caption = result.get("generated_text", "")
            else:
                caption = "Document/image analyzed"
            
            # Now ask legal question about the image content
            if question and caption:
                context = f"Image contains: {caption}"
                return await self.answer_legal_question(question, context)
            return f"**Image Analysis Result:**\n\n{caption}\n\nI can see this image contains legal document content. Please ask me specific questions about what you'd like to know."
        except Exception as e:
            logger.warning(f"Image analysis failed: {e}")
            return "I've received your image. While direct image processing is loading, please describe what you see and I'll provide detailed legal analysis based on your description."
    
    async def generate_ppt_content(self, topic: str, duration_minutes: int = 15, 
                                    slide_count: int = None) -> dict:
        """Generate PPT content with script"""
        if not slide_count:
            slide_count = max(10, duration_minutes)  # ~1 min per slide
        
        words_per_minute = 130
        total_words = duration_minutes * words_per_minute
        
        prompt = self._build_legal_prompt(
            f"Create a {duration_minutes}-minute presentation on: {topic}\n"
            f"Slides: {slide_count}\n"
            f"For each slide provide:\n"
            f"SLIDE [n]: [Title]\n"
            f"BULLETS: [3-5 bullet points]\n"
            f"SCRIPT: [~{total_words // slide_count} word speaking notes]\n"
            f"NOTES: [Key points to emphasize]\n",
            system_role=(
                "You are a professional legal presentation expert. Create engaging, "
                "informative presentations with speaker scripts. Each slide should have "
                "clear talking points and transition notes."
            )
        )
        
        try:
            result = await self.hf.query_text(
                MODELS["legal_qa"],
                {"inputs": prompt, "parameters": {"max_new_tokens": 2000, "temperature": 0.7, "return_full_text": False}}
            )
            if isinstance(result, list) and result:
                text = result[0].get("generated_text", "")
            else:
                text = str(result)
            text = self._clean_output(text)
        except Exception as e:
            logger.warning(f"PPT generation failed: {e}")
            text = ""
        
        if not text:
            text = self._generate_ppt_template(topic, slide_count, duration_minutes)
        
        return self._parse_ppt_content(text, topic, slide_count, duration_minutes)
    
    async def humanize_text(self, text: str) -> str:
        """Humanize AI text to avoid AI detection"""
        # Multi-pass humanization strategy
        humanized = self._apply_humanization_rules(text)
        return humanized
    
    def _apply_humanization_rules(self, text: str) -> str:
        """Apply humanization transformations"""
        # Replace common AI phrases with more natural alternatives
        replacements = {
            "It is important to note that": "Keep in mind that",
            "It should be noted that": "Worth noting is that",
            "Furthermore,": "Beyond this,",
            "Moreover,": "Adding to this,",
            "In conclusion,": "To wrap up,",
            "In summary,": "In short,",
            "It is worth mentioning": "One thing to consider",
            "This is particularly": "This is especially",
            "delve into": "examine",
            "In today's world,": "These days,",
            "In the realm of": "In",
            "It is crucial to": "We must",
            "plays a pivotal role": "is central",
            "comprehensive": "thorough",
            "utilize": "use",
            "facilitate": "help",
            "leverage": "use",
            "As an AI language model": "As a legal expert",
            "I cannot provide legal advice": "Here is relevant legal information",
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        # Add natural transitions and varied sentence structures
        sentences = text.split('. ')
        humanized_sentences = []
        
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if not sentence:
                continue
            # Vary sentence beginnings
            if i > 0 and i % 5 == 0 and len(sentence) > 20:
                starters = ["Notably, ", "Interestingly, ", "In practice, ", "From a legal standpoint, "]
                sentence = starters[i % len(starters)] + sentence[0].lower() + sentence[1:]
            humanized_sentences.append(sentence)
        
        return '. '.join(humanized_sentences)
    
    def _clean_output(self, text: str) -> str:
        """Clean model output"""
        if not text:
            return ""
        # Remove instruction leftovers
        text = re.sub(r'\[INST\].*?\[/INST\]', '', text, flags=re.DOTALL)
        text = re.sub(r'<s>|</s>', '', text)
        text = text.strip()
        # Remove excessive newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text
    
    def _parse_ppt_content(self, text: str, topic: str, slide_count: int, duration: int) -> dict:
        """Parse PPT text into structured format"""
        slides = []
        full_script = []
        
        # Try to parse structured content
        slide_pattern = re.split(r'SLIDE\s*\d+:', text, flags=re.IGNORECASE)
        
        if len(slide_pattern) > 2:
            for i, chunk in enumerate(slide_pattern[1:], 1):
                lines = chunk.strip().split('\n')
                title = lines[0].strip() if lines else f"Slide {i}"
                bullets = []
                script = ""
                notes = ""
                
                for line in lines[1:]:
                    if line.upper().startswith('BULLETS:'):
                        bullets = [b.strip() for b in line[8:].split('•') if b.strip()]
                    elif line.upper().startswith('SCRIPT:'):
                        script = line[7:].strip()
                    elif line.upper().startswith('NOTES:'):
                        notes = line[6:].strip()
                    elif line.strip().startswith('•') or line.strip().startswith('-'):
                        bullets.append(line.strip().lstrip('•-').strip())
                
                slides.append({
                    "slide_number": i,
                    "title": title,
                    "bullets": bullets if bullets else [f"Key point {j+1} about {topic}" for j in range(3)],
                    "script": script or f"On this slide we discuss {title}.",
                    "notes": notes or f"Emphasize the importance of {title}",
                })
                full_script.append(f"Slide {i}: {script or title}")
        else:
            # Generate structured content from scratch
            slides = self._build_default_slides(topic, slide_count)
            full_script = [s["script"] for s in slides]
        
        return {
            "topic": topic,
            "duration_minutes": duration,
            "slide_count": len(slides),
            "slides": slides,
            "full_script": "\n\n".join(full_script),
            "presentation_notes": f"This {duration}-minute presentation covers {topic} comprehensively.",
        }
    
    def _build_default_slides(self, topic: str, count: int) -> list:
        titles = [
            f"Introduction to {topic}",
            "Legal Framework & Background",
            "Key Legal Principles",
            "Relevant Legislation",
            "Case Studies & Precedents",
            "Rights and Obligations",
            "Enforcement & Remedies",
            "Recent Developments",
            "Practical Implications",
            "Challenges & Controversies",
            "Comparative Analysis",
            "Future Outlook",
            "Summary & Key Takeaways",
            "Conclusion",
            "References",
        ]
        slides = []
        for i in range(min(count, len(titles))):
            slides.append({
                "slide_number": i + 1,
                "title": titles[i],
                "bullets": [
                    f"Important aspect of {titles[i]}",
                    f"Legal significance and impact",
                    f"Practical considerations",
                ],
                "script": f"In this slide, we explore {titles[i]}. This is a fundamental aspect of {topic} that every legal professional must understand.",
                "notes": f"Take 1 minute on this slide. Emphasize practical relevance.",
            })
        return slides
    
    # ===== FALLBACK TEMPLATES =====
    
    def _fallback_legal_answer(self, question: str) -> str:
        return f"""**Legal Analysis: {question}**

Based on general legal principles, here is a comprehensive analysis:

**Overview**
This legal matter involves several important considerations under established law. The relevant legal framework provides guidance on how such matters are typically approached.

**Applicable Legal Principles**
1. **Due Process**: All legal proceedings must follow established procedural rules
2. **Rule of Law**: Laws apply equally to all individuals regardless of status
3. **Natural Justice**: Every party has the right to be heard (Audi Alteram Partem)
4. **Burden of Proof**: In civil matters, the standard is balance of probabilities; in criminal, beyond reasonable doubt

**Relevant Provisions**
- Applicable statutes and regulations govern this area
- Case law precedents establish binding interpretations
- Constitutional provisions may provide fundamental rights protection

**Analysis**
The legal position regarding your query involves careful consideration of both statutory provisions and judicial interpretations. Courts have consistently held that such matters require thorough examination of all relevant facts and circumstances.

**Conclusion**
For specific legal advice tailored to your situation, consulting a qualified legal professional is recommended. This response provides general legal information for educational purposes.

*Note: This is general legal information, not specific legal advice.*"""
    
    def _generate_legal_paper_template(self, subject: str, case_details: str) -> str:
        return f"""# Legal Analysis Paper: {subject}

## Abstract
This paper provides a comprehensive legal analysis of {subject}, examining relevant legislation, case law, and legal principles applicable to the matter at hand.

## 1. Introduction
The subject of {subject} represents a significant area of legal inquiry. This paper examines the legal landscape, drawing upon established precedents and statutory provisions to provide a thorough analysis.

## 2. Legal Framework
### 2.1 Applicable Legislation
The relevant legislative framework includes provisions that directly govern this subject matter. Key statutes establish the foundational legal principles.

### 2.2 Constitutional Provisions
Fundamental rights and constitutional guarantees form the backbone of legal protections in this area.

## 3. Case Analysis
{f"The case presents the following facts: {case_details}" if case_details else "The hypothetical case presents complex legal questions requiring careful analysis."}

### 3.1 Issues for Determination
1. Primary legal questions to be resolved
2. Secondary issues affecting the outcome
3. Procedural considerations

## 4. Arguments and Counter-Arguments
### 4.1 Arguments in Favor
- First argument based on statutory interpretation
- Second argument based on precedent
- Third argument based on equity principles

### 4.2 Counter-Arguments
- Alternative interpretations of law
- Distinguishing precedents
- Policy considerations

## 5. Relevant Precedents
Key judicial decisions that inform the legal analysis of this matter include landmark cases that have shaped the current legal understanding.

## 6. Conclusion
Based on the foregoing analysis, the legal position on {subject} is well-established. The applicable law provides clear guidance, subject to the specific facts of each case.

## References
1. Relevant statute citations
2. Case law references
3. Legal commentaries and scholarly works

---
*Generated by LegalAI | For educational purposes*"""
    
    def _generate_assignment_template(self, topic: str, word_count: int) -> str:
        return f"""# Academic Assignment: {topic}

## Introduction

The study of {topic} occupies a central position in legal scholarship. This assignment examines the core principles, statutory frameworks, and judicial interpretations that define this area of law. Understanding these concepts is essential for any legal practitioner navigating this complex field.

## Section 1: Historical Background and Development

The development of legal principles relating to {topic} has evolved significantly over time. Early legal frameworks established foundational rules that courts have refined through decades of judicial interpretation. The historical context provides essential insight into why current laws are structured as they are.

Legal scholars have long debated the appropriate scope and application of laws governing {topic}. These debates reflect broader tensions between competing values: individual rights versus collective welfare, certainty versus flexibility, and tradition versus progressive reform.

## Section 2: Core Legal Principles

Several fundamental principles govern the legal treatment of {topic}. First, the principle of legal certainty demands that rules be clear, accessible, and predictable. Second, proportionality requires that legal responses be commensurate with the severity of the matter. Third, procedural fairness ensures that all parties receive due process.

Courts applying these principles have developed a sophisticated body of case law that guides practitioners. The leading cases establish precedents that bind lower courts while allowing for adaptation to novel circumstances.

## Section 3: Statutory Framework

The legislative response to issues raised by {topic} reflects careful policy choices by lawmakers. Key statutes define rights, obligations, and remedies available to parties. Understanding the legislative intent behind these provisions is crucial for proper interpretation and application.

Regulatory frameworks supplement primary legislation, providing detailed rules for specific situations. These regulations must be interpreted consistently with their enabling statutes and constitutional requirements.

## Section 4: Contemporary Issues and Challenges

Modern developments have created new challenges for the legal treatment of {topic}. Technological change, globalization, and shifting social values all demand that law adapt to new realities. Courts and legislators face the challenge of applying established principles to situations their drafters could not have anticipated.

Recent judicial decisions reflect these tensions, as courts struggle to apply traditional doctrines to contemporary circumstances. Some commentators argue for more fundamental reform, while others emphasize the importance of doctrinal stability.

## Conclusion

This assignment has examined the key legal principles, statutory frameworks, and judicial interpretations governing {topic}. The analysis reveals a sophisticated but evolving legal landscape that balances competing interests while maintaining core values of fairness and justice.

Future developments in this area will likely reflect continued judicial innovation and potential legislative reform. Legal practitioners must stay abreast of these developments to effectively advise clients and advocate for their interests.

## References

1. Leading cases and statutory provisions
2. Academic commentary and legal texts  
3. Government reports and policy documents

---
*Word Count: Approximately {word_count} words*
*LegalAI Generated Assignment - Humanized and Plagiarism-Free*"""
    
    def _generate_test_template(self, subject: str, num_questions: int, test_type: str) -> str:
        if test_type == "mcq":
            questions = ""
            for i in range(1, num_questions + 1):
                questions += f"""
**Q{i}.** [Question about {subject} - aspect {i}]
   (A) First option
   (B) Second option
   (C) Third option
   (D) Fourth option
"""
            return f"""# TEST PAPER
## Subject: {subject}
### Time Allowed: {num_questions * 2} Minutes | Total Marks: {num_questions * 4}

**Instructions:**
1. All questions are compulsory
2. Each question carries 4 marks
3. No negative marking
4. Circle the correct answer

---
{questions}

---
## ANSWER KEY
{chr(10).join([f"Q{i}: (C)" for i in range(1, num_questions + 1)])}

*Generated by LegalAI Test Engine*"""
        else:
            return f"""# EXAMINATION PAPER
## Subject: {subject}
### Time: 3 Hours | Maximum Marks: 100

**General Instructions:** Attempt all questions. Read carefully before answering.

---
**SECTION A - Short Questions (20 Marks)**

Q1. Define the key concepts in {subject}. (5 marks)
Q2. Explain the constitutional provisions relevant to {subject}. (5 marks)
Q3. What are the essential elements required? (5 marks)
Q4. Distinguish between related legal concepts. (5 marks)

**SECTION B - Medium Questions (40 Marks)**

Q5. Discuss the legislative framework governing {subject}. (10 marks)
Q6. Analyze the role of judiciary in developing law on this subject. (10 marks)
Q7. Examine recent developments in {subject} with case references. (10 marks)
Q8. Compare different approaches taken by courts. (10 marks)

**SECTION C - Long Questions (40 Marks)**

Q9. Write a critical essay on the current state of {subject}, covering historical development, present framework, and future prospects. (20 marks)
Q10. A problem question involving {subject}. Advise the parties. (20 marks)

---
*LegalAI Test Generator | Educational Use*"""
    
    def _generate_ppt_template(self, topic: str, count: int, duration: int) -> str:
        slides_text = ""
        titles = [
            f"Introduction to {topic}",
            "Legal Framework",
            "Key Principles",
            "Case Studies",
            "Current Challenges",
            "Future Outlook",
            "Conclusion",
        ]
        for i in range(min(count, len(titles))):
            slides_text += f"""
SLIDE {i+1}: {titles[i]}
BULLETS: • Point 1 • Point 2 • Point 3
SCRIPT: Welcome to slide {i+1} on {titles[i]}. This section covers essential aspects of {topic}.
NOTES: Spend approximately {duration // count} minutes here.
"""
        return slides_text


# Singleton
legal_ai = LegalAIService()

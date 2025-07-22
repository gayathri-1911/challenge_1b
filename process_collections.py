#!/usr/bin/env python3
"""
Challenge 1b: Multi-Collection PDF Analysis
Persona-driven content extraction and analysis from PDF collections
"""

import os
import json
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import PyPDF2
from collections import defaultdict

class PersonaDrivenAnalyzer:
    def __init__(self):
        # Persona-specific keywords for relevance scoring
        self.persona_keywords = {
            "Travel Planner": {
                "high_priority": ["itinerary", "accommodation", "hotel", "restaurant", "attraction", "activity", 
                                "transport", "booking", "price", "cost", "budget", "group", "friends", "college",
                                "4 days", "trip", "travel", "visit", "tour", "sightseeing", "nightlife"],
                "medium_priority": ["culture", "history", "tradition", "food", "cuisine", "tips", "advice",
                                  "recommendation", "guide", "map", "location", "city", "beach", "coastal"],
                "low_priority": ["general", "overview", "introduction", "background"]
            },
            "HR professional": {
                "high_priority": ["form", "fillable", "onboarding", "compliance", "employee", "staff", "hire",
                                "document", "template", "workflow", "process", "signature", "e-signature",
                                "digital", "automation", "management", "tracking", "approval"],
                "medium_priority": ["create", "edit", "convert", "export", "share", "collaborate", "review",
                                  "acrobat", "pdf", "field", "checkbox", "dropdown", "text field"],
                "low_priority": ["basic", "introduction", "overview", "getting started"]
            },
            "Food Contractor": {
                "high_priority": ["vegetarian", "vegan", "gluten-free", "buffet", "catering", "corporate",
                                "dinner", "menu", "planning", "large group", "dietary", "restriction",
                                "allergen", "main course", "side dish", "appetizer", "serving"],
                "medium_priority": ["recipe", "ingredient", "cooking", "preparation", "kitchen", "chef",
                                  "nutrition", "healthy", "protein", "vegetables", "grains"],
                "low_priority": ["breakfast", "lunch", "snack", "dessert", "beverage"]
            }
        }
        
        # Section importance patterns
        self.importance_patterns = {
            "high": [r"essential", r"important", r"critical", r"must", r"required", r"key", r"main", r"primary"],
            "medium": [r"recommended", r"suggested", r"useful", r"helpful", r"consider", r"option"],
            "low": [r"optional", r"additional", r"extra", r"bonus", r"alternative"]
        }

    def extract_text_from_pdf(self, pdf_path: str) -> List[Dict]:
        """Extract text from PDF with page information"""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                pages_data = []
                
                for page_num, page in enumerate(pdf_reader.pages):
                    text = page.extract_text()
                    if text.strip():
                        pages_data.append({
                            "page_number": page_num,  # 0-based indexing
                            "text": text.strip()
                        })
                
                return pages_data
                
        except Exception as e:
            print(f"Error extracting text from {pdf_path}: {e}")
            return []

    def identify_sections(self, pages_data: List[Dict], document_name: str) -> List[Dict]:
        """Identify sections within the document"""
        sections = []
        
        for page_data in pages_data:
            text = page_data["text"]
            page_num = page_data["page_number"]
            
            # Split text into paragraphs
            paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
            
            for paragraph in paragraphs:
                # Look for section headers (lines that look like titles)
                lines = paragraph.split('\n')
                for i, line in enumerate(lines):
                    line = line.strip()
                    if len(line) > 10 and len(line) < 100:  # Reasonable title length
                        # Check if it looks like a section title
                        if (line.isupper() or 
                            line.istitle() or 
                            re.match(r'^[A-Z][a-z].*[^.]$', line) or
                            any(keyword in line.lower() for keyword in ['guide', 'tips', 'how to', 'introduction', 'overview'])):
                            
                            # Get some context (next few lines)
                            context_lines = lines[i+1:i+4] if i+1 < len(lines) else []
                            context = ' '.join(context_lines)
                            
                            sections.append({
                                "document": document_name,
                                "section_title": line,
                                "context": context,
                                "page_number": page_num,
                                "full_text": paragraph
                            })
        
        return sections

    def calculate_relevance_score(self, section: Dict, persona: str, job_description: str) -> float:
        """Calculate relevance score based on persona and job description"""
        score = 0.0
        text_to_analyze = (section["section_title"] + " " + section["context"]).lower()
        job_text = job_description.lower()
        
        # Get persona keywords
        keywords = self.persona_keywords.get(persona, {})
        
        # High priority keywords
        for keyword in keywords.get("high_priority", []):
            if keyword in text_to_analyze:
                score += 3.0
            if keyword in job_text and keyword in text_to_analyze:
                score += 2.0  # Bonus for job-specific relevance
        
        # Medium priority keywords
        for keyword in keywords.get("medium_priority", []):
            if keyword in text_to_analyze:
                score += 1.5
        
        # Low priority keywords
        for keyword in keywords.get("low_priority", []):
            if keyword in text_to_analyze:
                score += 0.5
        
        # Check for importance patterns
        for importance, patterns in self.importance_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_to_analyze):
                    if importance == "high":
                        score += 2.0
                    elif importance == "medium":
                        score += 1.0
                    else:
                        score += 0.3
        
        # Length bonus (longer sections might be more comprehensive)
        if len(section["full_text"]) > 500:
            score += 0.5
        
        return score

    def rank_sections(self, sections: List[Dict], persona: str, job_description: str) -> List[Dict]:
        """Rank sections by relevance to persona and job"""
        # Calculate scores
        for section in sections:
            section["relevance_score"] = self.calculate_relevance_score(section, persona, job_description)
        
        # Sort by relevance score (descending)
        ranked_sections = sorted(sections, key=lambda x: x["relevance_score"], reverse=True)
        
        # Assign importance ranks
        for i, section in enumerate(ranked_sections):
            section["importance_rank"] = i + 1
        
        return ranked_sections

    def generate_subsection_analysis(self, sections: List[Dict], max_sections: int = 5) -> List[Dict]:
        """Generate refined analysis for top sections"""
        subsection_analysis = []
        
        for section in sections[:max_sections]:
            # Refine the text by extracting key information
            refined_text = self.refine_section_text(section["full_text"])
            
            subsection_analysis.append({
                "document": section["document"],
                "refined_text": refined_text,
                "page_number": section["page_number"]
            })
        
        return subsection_analysis

    def refine_section_text(self, text: str) -> str:
        """Refine section text to extract key information"""
        # Split into sentences
        sentences = re.split(r'[.!?]+', text)
        
        # Filter and rank sentences
        important_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 20:  # Ignore very short sentences
                # Simple importance scoring
                importance_score = 0
                if any(word in sentence.lower() for word in ['important', 'key', 'essential', 'must', 'should']):
                    importance_score += 2
                if any(word in sentence.lower() for word in ['recommend', 'suggest', 'consider', 'tip']):
                    importance_score += 1
                
                important_sentences.append((sentence, importance_score))
        
        # Sort by importance and take top sentences
        important_sentences.sort(key=lambda x: x[1], reverse=True)
        top_sentences = [sent[0] for sent in important_sentences[:3]]
        
        return '. '.join(top_sentences) + '.' if top_sentences else text[:200] + '...'

    def process_collection(self, collection_path: str) -> Dict:
        """Process a single collection"""
        collection_path = Path(collection_path)
        
        # Load input configuration
        input_file = collection_path / "challenge1b_input.json"
        if not input_file.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")
        
        with open(input_file, 'r', encoding='utf-8') as f:
            input_config = json.load(f)
        
        # Extract configuration
        documents = input_config["documents"]
        persona = input_config["persona"]["role"]
        job_description = input_config["job_to_be_done"]["task"]
        
        print(f"Processing collection: {collection_path.name}")
        print(f"Persona: {persona}")
        print(f"Job: {job_description}")
        print(f"Documents: {len(documents)}")
        
        # Process all documents
        all_sections = []
        processed_docs = []
        
        pdfs_dir = collection_path / "PDFs"
        for doc_info in documents:
            pdf_path = pdfs_dir / doc_info["filename"]
            if pdf_path.exists():
                print(f"  Processing: {doc_info['filename']}")
                pages_data = self.extract_text_from_pdf(str(pdf_path))
                sections = self.identify_sections(pages_data, doc_info["filename"])
                all_sections.extend(sections)
                processed_docs.append(doc_info["filename"])
            else:
                print(f"  Warning: File not found: {pdf_path}")
        
        # Rank sections by relevance
        ranked_sections = self.rank_sections(all_sections, persona, job_description)
        
        # Generate output
        output = {
            "metadata": {
                "input_documents": processed_docs,
                "persona": persona,
                "job_to_be_done": job_description,
                "processing_timestamp": datetime.now().isoformat()
            },
            "extracted_sections": [
                {
                    "document": section["document"],
                    "section_title": section["section_title"],
                    "importance_rank": section["importance_rank"],
                    "page_number": section["page_number"]
                }
                for section in ranked_sections[:10]  # Top 10 sections
            ],
            "subsection_analysis": self.generate_subsection_analysis(ranked_sections, max_sections=5)
        }
        
        return output

def process_all_collections():
    """Process all collections in Challenge 1b"""
    base_dir = Path("/app/collections")  # Docker path
    if not base_dir.exists():
        base_dir = Path(".")  # Local development path
    
    analyzer = PersonaDrivenAnalyzer()
    
    # Find all collection directories
    collection_dirs = [d for d in base_dir.iterdir() if d.is_dir() and d.name.startswith("Collection")]
    
    if not collection_dirs:
        print("No collection directories found")
        return
    
    print(f"Found {len(collection_dirs)} collections to process")
    
    for collection_dir in sorted(collection_dirs):
        try:
            print(f"\n{'='*50}")
            result = analyzer.process_collection(collection_dir)
            
            # Save output
            output_file = collection_dir / "challenge1b_output_generated.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=4, ensure_ascii=False)
            
            print(f"✓ Generated output: {output_file}")
            print(f"  Extracted sections: {len(result['extracted_sections'])}")
            print(f"  Subsection analyses: {len(result['subsection_analysis'])}")
            
        except Exception as e:
            print(f"✗ Error processing {collection_dir.name}: {e}")

if __name__ == "__main__":
    print("Starting Challenge 1b: Multi-Collection PDF Analysis...")
    process_all_collections()
    print("Challenge 1b processing completed!")

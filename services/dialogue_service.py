"""
Socratic dialogue service for expert knowledge contribution.
Uses Gemini to guide domain experts through a rigorous, evidence-based
dialogue that produces verified knowledge claims for the RAG.
"""
import logging
import os
import re
from typing import Dict, List, Optional

import google.genai as genai

logger = logging.getLogger(__name__)


class SocraticDialogue:
    """Manages Socratic expert dialogue for knowledge base contribution."""

    MODEL = "gemini-2.0-flash"

    CATEGORIES = [
        "dietary_fats",
        "food_mental_health",
        "keto_diet",
        "supplements",
        "metabolic_health",
        "behaviour_change",
        "clinical_evidence",
    ]

    def __init__(self):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY is required for dialogue service")
        self.client = genai.Client(api_key=api_key)

    def process_turn(
        self,
        messages: List[Dict],
        new_message: str,
        topic: str,
        consensus_points: List[Dict],
        related_context: str,
    ) -> Dict:
        """Process one turn of the Socratic dialogue.

        Args:
            messages: Chat history [{role: "expert"|"assistant", content: str}]
            new_message: The expert's latest message
            topic: Current topic being discussed
            consensus_points: Points confirmed so far
            related_context: Existing RAG content related to the message

        Returns:
            {reply: str, consensus_point: dict|None}
        """
        system_prompt = self._build_system_prompt(topic, consensus_points, related_context)

        # Build Gemini message format
        gemini_contents = []

        # System instruction as first user turn
        gemini_contents.append({
            "role": "user",
            "parts": [{"text": system_prompt}]
        })
        gemini_contents.append({
            "role": "model",
            "parts": [{"text": "Understood. I'm ready to work with you on contributing knowledge to the metabolic mental health knowledge base. What would you like to discuss?"}]
        })

        # Replay chat history
        for msg in messages:
            role = "user" if msg["role"] in ("user", "expert") else "model"
            gemini_contents.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })

        # Add new message
        gemini_contents.append({
            "role": "user",
            "parts": [{"text": new_message}]
        })

        response = self.client.models.generate_content(
            model=self.MODEL,
            contents=gemini_contents,
        )

        reply = response.text
        consensus_point = self._extract_consensus_point(reply)

        return {
            "reply": reply,
            "consensus_point": consensus_point,
        }

    def generate_article(
        self,
        topic: str,
        consensus_points: List[Dict],
        category: str,
    ) -> str:
        """Generate a markdown knowledge base article from confirmed consensus points."""
        points_text = "\n".join([
            f"- {cp['claim']} [Evidence: {cp.get('evidence_level', 'not specified')}] "
            f"[Sources: {cp.get('sources', cp.get('citations', 'none'))}]"
            for cp in consensus_points
        ])

        prompt = f"""Generate a well-structured markdown knowledge base article from these verified consensus points.

Topic: {topic}
Category: {category}

Consensus Points:
{points_text}

Requirements:
- Start with a # heading (the article title)
- Use ## subheadings for each major point
- Include inline citations where relevant
- Add a ## References section at the end with all cited sources
- Use clear, educational language suitable for a metabolic health knowledge base
- Keep claims precise and evidence-qualified (e.g., "has been shown to" not "definitely causes")
- Article should be 300-800 words
- Do not add information beyond what the consensus points contain
"""

        response = self.client.models.generate_content(
            model=self.MODEL,
            contents=prompt,
        )

        return response.text

    def _build_system_prompt(
        self,
        topic: str,
        consensus_points: List[Dict],
        related_context: str,
    ) -> str:
        confirmed_lines = []
        for i, cp in enumerate(consensus_points):
            if isinstance(cp, str):
                confirmed_lines.append(f"- [{i+1}] {cp}")
            elif isinstance(cp, dict):
                claim = cp.get("claim", str(cp))
                ev = cp.get("evidence_level", "?")
                src = cp.get("sources", "none")
                confirmed_lines.append(f"- [{i+1}] {claim} (Evidence: {ev}, Sources: {src})")
        confirmed = "\n".join(confirmed_lines) or "None yet."

        categories_str = ", ".join(self.CATEGORIES)

        return f"""You are a rigorous but collaborative knowledge editor for a metabolic psychiatry knowledge base called Hushful.

Your role: Help domain experts contribute verified, well-sourced knowledge claims. You use Socratic questioning to ensure claims are specific, evidence-based, and accurate. The goal is to build the best available metabolic mental health knowledge guide in the world.

## Current Topic: {topic or 'Not yet set - ask the expert what they want to contribute'}

## Confirmed Consensus Points:
{confirmed}

## Related Existing Knowledge in Our Database:
{related_context or 'No closely related articles found.'}

## Your Dialogue Approach:

1. **When an expert states a claim:**
   - Acknowledge the claim
   - Check specificity: Is the dose, population, effect size, or mechanism clear?
   - Ask for supporting evidence: "What evidence supports this? Any specific studies or guidelines?"
   - Check against existing knowledge: Does this contradict or extend what we already have?

2. **When an expert provides a citation:**
   - Ask clarifying questions about the study (sample size, type of trial, population)
   - Note if it's a single study vs meta-analysis/systematic review vs clinical guideline
   - Ask about limitations or contradictory findings

3. **When you're satisfied a point is well-supported:**
   - Summarise the consensus point clearly
   - Include the key claim, evidence level, and citations
   - Format EXACTLY as: [CONSENSUS_POINT]claim text|evidence_level|citation1, citation2[/CONSENSUS_POINT]
   - Evidence levels: meta-analysis, RCT, observational, case-series, expert-opinion, mechanistic
   - Ask the expert to confirm before moving on

4. **When all points for a topic are confirmed:**
   - Propose finalising the article
   - Suggest a category from: {categories_str}

## Rules:
- Be sceptical of claims without evidence, but not dismissive
- Distinguish between correlation and causation
- Note when evidence is preliminary vs well-established
- Ask about contraindications and populations where claims may not apply
- NEVER fabricate citations or studies
- Keep the tone collaborative and respectful — this is a peer dialogue, not an exam
- If the expert is clearly knowledgeable, match their level of technical detail
- Remember: this knowledge base serves people managing their metabolic mental health, so accuracy matters
"""

    @staticmethod
    def _extract_consensus_point(reply_text: str) -> Optional[Dict]:
        """Extract a consensus point from the bot's reply if present."""
        match = re.search(
            r'\[CONSENSUS_POINT\](.*?)\|(.*?)\|(.*?)\[/CONSENSUS_POINT\]',
            reply_text,
            re.DOTALL,
        )
        if match:
            return {
                "claim": match.group(1).strip(),
                "evidence_level": match.group(2).strip(),
                "sources": match.group(3).strip(),
                "confirmed": False,
            }
        return None

import anthropic
import os
from typing import List, Dict


class DraftGenerator:

    def __init__(self):
        self.client = anthropic.Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )

    def generate(self, evidence: List[Dict], draft_type: str = "case_summary",
                 preferences: List[str] = None) -> Dict:

        if not evidence:
            return {"draft": "No evidence found.", "grounded": False}

        # Evidence format করো
        evidence_text = "\n\n".join([
            f"[Page {e['page']} | Relevance: {e.get('relevance')}]\n{e['text']}"
            for e in evidence
        ])

        # Preferences যোগ করো
        pref_text = ""
        if preferences:
            pref_text = "\n\nApply these operator preferences:\n" + \
                        "\n".join(f"- {p}" for p in preferences[:5])

        prompt = f"""You are a legal assistant at Pearson Specter Litt.

RULES:
- Use ONLY the evidence below. Do not add unsupported facts.
- Mark anything not in evidence as [NOT IN DOCUMENTS].
- Be precise and professional.
{pref_text}

Write a structured Case Fact Summary with:
1. PARTIES INVOLVED
2. KEY FACTS
3. IMPORTANT DATES
4. CORE LEGAL ISSUES
5. DAMAGES/AMOUNTS

EVIDENCE:
{evidence_text}
"""

        response = self.client.messages.create(
            model      = "claude-sonnet-4-20250514",
            max_tokens = 1500,
            messages   = [{"role": "user", "content": prompt}]
        )

        return {
            "draft"         : response.content[0].text,
            "evidence_used" : evidence,
            "citations"     : [f"Page {e['page']}" for e in evidence],
            "grounded"      : True,
            "evidence_count": len(evidence)
        }
# taxonomy.py — human-readable titles for the industry references each attack maps to.
#
# IDs verified against:
#   OWASP Top 10 for LLM Applications (2025) — https://genai.owasp.org/
#   MITRE ATLAS                              — https://atlas.mitre.org/

OWASP_LLM = {
    "LLM01:2025": "Prompt Injection",
    "LLM02:2025": "Sensitive Information Disclosure",
    "LLM07:2025": "System Prompt Leakage",
}

ATLAS = {
    "AML.T0051": "LLM Prompt Injection",
    "AML.T0051.000": "LLM Prompt Injection: Direct",
    "AML.T0051.001": "LLM Prompt Injection: Indirect",
}


def title(ref_id):
    """Return the human-readable title for an OWASP-LLM or ATLAS id.

    Falls back to the id itself if it isn't in either table, so an unmapped
    reference still prints something sensible rather than raising.
    """
    return OWASP_LLM.get(ref_id) or ATLAS.get(ref_id) or ref_id

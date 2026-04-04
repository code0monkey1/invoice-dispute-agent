from langchain.tools import tool
from typing import Dict, Any
from tavily import TavilyClient

tavily_client = TavilyClient()


@tool
def lookup_small_claims_procedures(jurisdiction: str) -> Dict[str, Any]:
    """Search for small claims court filing procedures in a specific jurisdiction."""
    return tavily_client.search(
        f"small claims court filing procedure {jurisdiction} how to file freelancer unpaid invoice"
    )


@tool
def generate_court_filing_guide(jurisdiction: str) -> Dict[str, Any]:
    """Search for a step-by-step guide to filing in small claims court for the given jurisdiction."""
    return tavily_client.search(
        f"step by step guide file small claims court {jurisdiction} freelancer unpaid invoice amount limit"
    )

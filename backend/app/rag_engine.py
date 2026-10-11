class RAGEngine:
    """Expose injected product context only when a customer asks a product FAQ."""

    def __init__(self, custom_context: str = ""):
        self.custom_context = custom_context

    def query(self, user_text: str) -> str:
        """Return configured context for product questions; do not invent facts."""
        text = user_text.lower()
        product_terms = [
            "processing fee", "fee", "fees", "charges", "cost", "processing time",
            "doorstep", "verification", "how much time", "how long", "branch",
            "offer details", "product details", "what is the process",
            "शुल्क", "फीस", "कीमत", "लागत", "प्रक्रिया", "घर पर सत्यापन", "कितना समय", "शाखा", "ऑफर की जानकारी",
        ]
        if any(term in text for term in product_terms):
            return self.custom_context.strip()
        return ""

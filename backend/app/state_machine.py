from dataclasses import dataclass, field, asdict
from enum import Enum
import re
from typing import Optional, Dict, Any, List, Tuple

class Stage(str, Enum):
    INITIAL = "INITIAL"
    VERIFY_CUSTOMER = "VERIFY_CUSTOMER"
    OFFER_PITCH = "OFFER_PITCH"
    QUALIFICATION = "QUALIFICATION"
    NEGOTIATING_LOAN_AMOUNT = "NEGOTIATING_LOAN_AMOUNT"
    BUSY_CALLBACK_PENDING = "BUSY_CALLBACK_PENDING"
    BUSY_CALLBACK = "BUSY_CALLBACK"
    TRANSFERRED_SPECIALIST = "TRANSFERRED_SPECIALIST"
    DISQUALIFIED = "DISQUALIFIED"
    QUALIFIED_HANDOFF = "QUALIFIED_HANDOFF"
    CALL_ENDED = "CALL_ENDED"

class PropertyType(str, Enum):
    RESIDENTIAL = "Residential"
    COMMERCIAL = "Commercial"
    INDUSTRIAL = "Industrial"
    AGRICULTURAL = "Agricultural"

class OwnershipStatus(str, Enum):
    SOLE = "Sole"
    JOINT = "Joint"

class OccupationType(str, Enum):
    SALARIED = "Salaried"
    SELF_EMPLOYED = "Self-Employed"

class IncomeMode(str, Enum):
    BANK = "Bank"
    CASH = "Cash"

@dataclass
class QualificationState:
    customer_verified: Optional[bool] = None
    is_busy: bool = False
    callback_time: Optional[str] = None
    transfer_intent: Optional[str] = None
    
    property_type: Optional[str] = None
    ownership_status: Optional[str] = None
    documents_available: Optional[bool] = None
    loan_amount: Optional[int] = None
    occupation: Optional[str] = None
    income_mode: Optional[str] = None
    market_value: Optional[str] = None
    tenure_years: Optional[int] = None
    
    pending_loan_amount_negotiation: Optional[int] = None
    disqualified: bool = False
    disqualification_reason: Optional[str] = None
    transferred: bool = False
    transfer_reason: Optional[str] = None
    qualified: bool = False
    current_stage: Stage = Stage.INITIAL
    history: List[Dict[str, str]] = field(default_factory=list)

    def is_checklist_complete(self) -> bool:
        return (
            self.property_type is not None and
            self.ownership_status is not None and
            self.documents_available is not None and
            self.loan_amount is not None and
            self.occupation is not None and
            self.income_mode is not None and
            self.market_value is not None and
            self.tenure_years is not None
        )

    def get_missing_checklist_items(self) -> List[str]:
        missing = []
        if self.property_type is None:
            missing.append("property_type")
        if self.ownership_status is None:
            missing.append("ownership_status")
        if self.documents_available is None:
            missing.append("documents_available")
        if self.loan_amount is None:
            missing.append("loan_amount")
        if self.occupation is None or self.income_mode is None:
            missing.append("occupation_and_income")
        if self.market_value is None:
            missing.append("market_value")
        if self.tenure_years is None:
            missing.append("tenure")
        return missing

    def get_first_missing_question_key(self) -> Optional[str]:
        missing = self.get_missing_checklist_items()
        return missing[0] if missing else None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["current_stage"] = self.current_stage.value
        data["missing_items"] = self.get_missing_checklist_items()
        data["is_complete"] = self.is_checklist_complete()
        return data


class VoiceAgentStateMachine:
    """
    Implements the 'Extract First, Validate Second, Update State Third, Ask Next Question Fourth' architecture.
    Handles out-of-order entity extraction, immediate disqualification, loan transfer cases,
    busy callbacks, and senior expert handoffs.
    """

    def __init__(self, config: Optional[Any] = None):
        self.config = config
        self.state = QualificationState()

    def reset(self):
        self.state = QualificationState()

    def _localized(self, english: str, hindi: str) -> str:
        if self.config and self.config.language_to_speak.strip().lower() == "hindi":
            return hindi
        return english

    def _is_negated_match(self, text: str, match: re.Match) -> bool:
        negations = {"not", "no", "never", "dont", "don't", "doesnt", "doesn't", "isnt", "isn't", "नहीं", "नही", "मत"}
        prefix = text[max(0, match.start() - 64):match.start()]
        prefix = re.split(r"[,;.!?।]|\b(?:but|however|although|instead)\b", prefix)[-1]
        words = re.findall(r"[a-z']+|[\u0900-\u097f]+", prefix)
        if any(word in negations for word in words[-6:]):
            return True

        suffix = text[match.end():match.end() + 24].lstrip()
        return bool(re.match(r"(?:(?:में|से|का|की|के)\s+)?(?:नहीं|नही|मत)", suffix))

    def _latest_choice(self, text: str, choices: Dict[Any, List[str]]) -> Optional[Any]:
        """Return the last clearly stated choice, skipping directly negated mentions."""
        matches = []
        for value, phrases in choices.items():
            for phrase in phrases:
                escaped = re.escape(phrase).replace(r"\ ", r"\s+")
                if re.fullmatch(r"[a-z0-9' -]+", phrase):
                    pattern = rf"(?<![a-z0-9]){escaped}(?![a-z0-9])"
                else:
                    pattern = rf"(?<!\w){escaped}(?!\w)"
                for match in re.finditer(pattern, text):
                    if self._is_negated_match(text, match):
                        continue
                    matches.append((match.start(), value))
        return max(matches, key=lambda item: item[0])[1] if matches else None

    def _contains_non_negated_phrase(self, text: str, phrases: List[str]) -> bool:
        for phrase in phrases:
            escaped = re.escape(phrase).replace(r"\ ", r"\s+")
            if re.fullmatch(r"[a-z0-9' -]+", phrase):
                pattern = rf"(?<![a-z0-9]){escaped}(?![a-z0-9])"
            else:
                pattern = rf"(?<!\w){escaped}(?!\w)"
            for match in re.finditer(pattern, text):
                if self._is_negated_match(text, match):
                    continue
                return True
        return False

    def _record_extracted_entities(self, extracted: Dict[str, Any]) -> None:
        for field_name in (
            "property_type", "ownership_status", "documents_available",
            "occupation", "income_mode", "market_value", "tenure_years",
        ):
            if field_name in extracted:
                setattr(self.state, field_name, extracted[field_name])

    def _eligibility_failure(self) -> Optional[str]:
        if self.state.property_type == PropertyType.AGRICULTURAL.value:
            return "agricultural"
        if self.state.documents_available is False:
            return "documents"
        if self.state.income_mode == IncomeMode.CASH.value:
            return "cash_income"
        if self.state.tenure_years is not None and not 3 <= self.state.tenure_years <= 15:
            return "tenure"
        return None

    def _disqualification_reply(self, failure: str, customer_name: str, company_name: str) -> str:
        messages = {
            "agricultural": (
                f"Thank you for the information, {customer_name}. Agricultural properties are not eligible for this pre-approved offer. We appreciate your time with {company_name}.",
                f"जानकारी देने के लिए धन्यवाद, {customer_name} जी। कृषि भूमि इस पूर्व-मंज़ूर प्रस्ताव के लिए पात्र नहीं है। {company_name} को अपना समय देने के लिए धन्यवाद।",
                "Agricultural properties are not eligible for this LAP offer.",
            ),
            "documents": (
                f"Thank you for sharing, {customer_name}. Original property documents must be available for verification, so we cannot proceed with this offer today. Thank you for your time with {company_name}.",
                f"जानकारी देने के लिए धन्यवाद, {customer_name} जी। इस प्रस्ताव के लिए मूल संपत्ति दस्तावेज़ सत्यापन हेतु उपलब्ध होना ज़रूरी है, इसलिए हम आज आगे नहीं बढ़ सकते। {company_name} को अपना समय देने के लिए धन्यवाद।",
                "Original property documents are mandatory for verification.",
            ),
            "cash_income": (
                f"Thank you for the details, {customer_name}. Income must be received through a bank for this offer. Since your income is in cash, we cannot proceed today. Thank you for your time with {company_name}.",
                f"जानकारी देने के लिए धन्यवाद, {customer_name} जी। इस प्रस्ताव के लिए आय बैंक खाते में आना ज़रूरी है। नकद आय होने के कारण हम आज आगे नहीं बढ़ सकते। {company_name} को अपना समय देने के लिए धन्यवाद।",
                "Income received in cash is not eligible; bank credit is mandatory.",
            ),
            "tenure": (
                f"Thank you, {customer_name}. The repayment tenure must be between 3 and 15 years. Your requested tenure is outside this range, so we cannot proceed with this offer today. Thank you for your time with {company_name}.",
                f"धन्यवाद, {customer_name} जी। ऋण चुकाने की अवधि 3 से 15 साल के बीच होनी चाहिए। आपकी बताई अवधि इस सीमा से बाहर है, इसलिए हम इस प्रस्ताव पर आगे नहीं बढ़ सकते। {company_name} को अपना समय देने के लिए धन्यवाद।",
                f"Tenure of {self.state.tenure_years} years is outside the eligible range (3-15 years).",
            ),
        }
        english, hindi, reason = messages[failure]
        self.state.disqualified = True
        self.state.disqualification_reason = reason
        self.state.current_stage = Stage.DISQUALIFIED
        return self._localized(english, hindi)

    def _transfer_reply(self, customer_name: str, company_name: str, intent: str) -> str:
        self.state.transfer_intent = intent
        self.state.transferred = True
        self.state.transfer_reason = "Existing loan / EMI transfer request detected"
        self.state.current_stage = Stage.TRANSFERRED_SPECIALIST
        return self._localized(
            f"Thank you for sharing that, {customer_name}. A loan transfer specialist will contact you shortly about your existing property loan or EMI request. Thank you for your time with {company_name}.",
            f"यह जानकारी देने के लिए धन्यवाद, {customer_name} जी। आपकी संपत्ति पर मौजूदा ऋण या किस्त से जुड़े अनुरोध के बारे में ऋण हस्तांतरण विशेषज्ञ आपसे जल्द संपर्क करेंगे। {company_name} को अपना समय देने के लिए धन्यवाद।",
        )

    def _extract_callback_time(self, text: str) -> Optional[str]:
        relative = re.search(
            r"\b(?:in|after)\s+\d+\s*(?:minutes?|mins?|hours?|hrs?)\b|\b\d+\s*(?:minutes?|mins?|hours?|hrs?)\s+later\b|\d+\s*(?:मिनट|मिनटों|घंटे|घंटों)\s बाद",
            text,
        )
        if relative:
            return relative.group(0).strip()
        clock = re.search(
            r"\bat\s+\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?|am|pm)?|\b\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?|am|pm|बजे)",
            text,
        )
        daypart = re.search(
            r"\b(?:tomorrow|today|tonight|morning|afternoon|evening|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b|कल|आज|सुबह|दोपहर|शाम|सोमवार|मंगलवार|बुधवार|गुरुवार|शुक्रवार|शनिवार|रविवार",
            text,
        )
        if clock:
            start = daypart.start() if daypart and daypart.start() < clock.start() else clock.start()
            return text[start:clock.end()].strip()
        if daypart:
            return daypart.group(0).strip()
        return None

    def _is_wrong_person_utterance(self, text: str, customer_name: str) -> bool:
        named_customer = customer_name.lower().strip()
        first_name = named_customer.split()[0] if named_customer else ""
        return (
            any(w in text for w in ["wrong number", "not him", "not her", "गलत नंबर", "वह यहाँ नहीं", "वे यहाँ नहीं"])
            or text.strip() in {"no", "nope", "नहीं"}
            or bool(named_customer and ("not " + named_customer) in text)
            or bool(first_name and re.search(rf"\bnot\s+(?:the\s+)?{re.escape(first_name)}\b", text))
        )

    def extract_entities(self, text: str) -> Dict[str, Any]:
        """
        Extract all possible eligibility information and conversational cues from customer utterance.
        """
        extracted = {}
        t = text.lower().strip()

        busy_denial = any(w in t for w in ["not busy", "not in a meeting", "व्यस्त नहीं"])
        callback_requested = any(w in t for w in ["call me", "phone me", "call back", "फ़ोन करें", "फोन करें", "बाद में कॉल", "बाद में फोन"])
        if not busy_denial and (callback_requested or any(w in t for w in ["busy", "in a meeting", "driving", "call later", "not a good time", "not now", "no time", "can't talk", "cannot talk", "मीटिंग में", "व्यस्त", "अभी बात नहीं"])):
            extracted["is_busy"] = True
            extracted["callback_time"] = self._extract_callback_time(t) or "later"

        has_existing_loan = self._contains_non_negated_phrase(t, [
            "already have a loan", "already have loan", "existing loan", "current loan",
            "loan on this property", "loan against this property", "active loan on property",
            "balance transfer", "transfer my loan", "loan chal raha", "पहले से लोन", "पहले से ऋण",
            "पहले से कर्ज", "मौजूदा लोन", "मौजूदा ऋण",
        ])
        asks_to_reduce_emi = self._contains_non_negated_phrase(t, [
            "reduce emi", "reduce my emi", "reduce the emi", "lower emi", "lower my emi", "emi reduction", "emi kam", "emi kam karna",
            "किस्त कम", "ईएमआई कम", "ईएमआई घटाना", "किस्त घटाना", "बैलेंस ट्रांसफर",
        ])
        if has_existing_loan or asks_to_reduce_emi:
            extracted["transfer_intent"] = "existing_loan" if has_existing_loan else "emi_reduction"

        property_type = self._latest_choice(t, {
            PropertyType.AGRICULTURAL.value: ["agricultural", "agriculture", "farmland", "farm land", "kheti", "कृषि", "खेती", "खेत"],
            PropertyType.COMMERCIAL.value: ["commercial", "dukan", "shop", "office", "व्यावसायिक", "दुकान", "कार्यालय"],
            PropertyType.INDUSTRIAL.value: ["industrial", "factory", "warehouse", "औद्योगिक", "कारखाना", "फैक्टरी"],
            PropertyType.RESIDENTIAL.value: ["residential", "house", "flat", "apartment", "my home", "the home", "makan", "आवासीय", "मकान", "घर", "फ्लैट"],
        })
        if property_type:
            extracted["property_type"] = property_type

        ownership = self._latest_choice(t, {
            OwnershipStatus.JOINT.value: ["joint", "jointly", "wife", "husband", "brother", "partner", "father", "family", "संयुक्त", "पत्नी", "पति", "भाई", "परिवार", "साझा"],
            OwnershipStatus.SOLE.value: ["sole", "my own", "myself", "alone", "single", "my name", "only me", "अकेले", "मेरे नाम", "सिर्फ मेरा", "केवल मेरा"],
        })
        if ownership:
            extracted["ownership_status"] = ownership

        document_status = self._latest_choice(t, {
            False: [
                "no original", "no originals", "not original", "not the originals",
                "originals unavailable", "original documents unavailable", "original documents are not available",
                "don't have original", "do not have original", "don't have originals", "do not have originals",
                "don't have the originals", "do not have the originals",
                "only photocopies", "photocopies only", "only xerox", "xerox only", "only copies", "copies only",
                "not originals", "original documents missing", "original papers missing", "lost original documents",
                "मूल दस्तावेज नहीं", "मूल दस्तावेज़ नहीं", "मूल कागज़ नहीं", "मूल कागज नहीं", "मूल कागजात नहीं",
                "केवल फोटोकॉपी", "सिर्फ फोटोकॉपी", "sirf photocopy", "sirf xerox", "सिर्फ फोटो कॉपी", "केवल फोटो कॉपी", "केवल ज़ेरॉक्स", "केवल जेरॉक्स", "मूल दस्तावेज़ गुम",
            ],
            True: [
                "original papers available", "originals available", "original documents available",
                "original documents are available", "original papers are available", "have original",
                "have the original", "have the originals", "have originals", "original documents ready", "original papers ready",
                "originals are ready", "originals at home", "original documents at home", "original papers are at home",
                "मूल दस्तावेज उपलब्ध", "मूल दस्तावेज़ उपलब्ध", "मूल कागजात उपलब्ध", "मूल दस्तावेज घर पर",
                "मूल दस्तावेज़ घर पर", "मूल कागजात घर पर", "असली कागजात उपलब्ध", "मूल दस्तावेज मेरे पास", "मूल कागजात मेरे पास",
            ],
        })
        if document_status is not None:
            extracted["documents_available"] = document_status

        loan_amount_val = None
        market_val = None

        if any(w in t for w in ["worth", "market value", "value is", "cost", "valued at", "बाजार मूल्य", "कीमत", "मूल्य"]):
            market_matches = list(re.finditer(r"(?:worth|market value|value is|valued at|cost|बाजार मूल्य|कीमत|मूल्य|लगभग|करीब|actually|rather|instead|make it)\s*(?:is\s*)?(?:about|around|करीब|लगभग)?\s*(?:rs\.?|inr|₹)?\s*(\d+(?:\.\d+)?)\s*(crore|crores|cr|lakh|lakhs|lacs|lac|करोड़|लाख)?", t))
            mv_match = market_matches[-1] if market_matches else None
            if mv_match:
                amt_num = float(mv_match.group(1))
                unit = mv_match.group(2) or ""
                if "cr" in unit or "crore" in unit or "करोड़" in unit:
                    market_val = f"₹{amt_num} करोड़" if "करोड़" in unit or self._localized("", "Hindi") == "Hindi" else f"₹{amt_num} Crore"
                elif "lakh" in unit or "lac" in unit or "लाख" in unit:
                    market_val = f"₹{amt_num} लाख" if "लाख" in unit or self._localized("", "Hindi") == "Hindi" else f"₹{amt_num} Lakhs"
                else:
                    market_val = f"₹{amt_num:,.0f}"

        loan_matches = list(re.finditer(r"(?:need|borrow|loan of|want|looking for|require|amount of|चाहिए|राशि|ऋण|लोन लेना है|उधार|actually|rather|instead|make it)\s*(?:about|around|लगभग|करीब)?\s*(?:rs\.?|inr|₹)?\s*(\d+(?:\.\d+)?)\s*(crore|crores|cr|lakh|lakhs|lacs|lac|करोड़|लाख)?", t))
        loan_match = loan_matches[-1] if loan_matches else None
        if loan_match:
            num = float(loan_match.group(1))
            unit = loan_match.group(2) or ""
            if "cr" in unit or "crore" in unit or "करोड़" in unit:
                loan_amount_val = int(num * 10000000)
            elif "lakh" in unit or "lac" in unit or "लाख" in unit or "l" in unit:
                loan_amount_val = int(num * 100000)
            else:
                loan_amount_val = int(num) if num > 10000 else int(num * 100000)
        else:
            lakh_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:lakh|lakhs|lacs|lac|l|लाख)\b", t)
            if lakh_match and not ("worth" in t or "value" in t):
                loan_amount_val = int(float(lakh_match.group(1)) * 100000)

        if loan_amount_val is not None:
            extracted["loan_amount"] = loan_amount_val
        if market_val is not None:
            extracted["market_value"] = market_val

        occupation = self._latest_choice(t, {
            OccupationType.SALARIED.value: ["salaried", "job", "employee", "working in", "it firm", "नौकरी", "नौकरीपेशा", "वेतनभोगी"],
            OccupationType.SELF_EMPLOYED.value: ["self employed", "self-employed", "business", "freelance", "shopkeeper", "retail", "doctor", "ca", "स्वरोजगार", "व्यवसाय", "कारोबार", "अपना काम"],
        })
        if occupation:
            extracted["occupation"] = occupation

        income_mode = self._latest_choice(t, {
            IncomeMode.CASH.value: ["cash", "cash in hand", "payments in cash", "नकद", "कैश"],
            IncomeMode.BANK.value: ["bank", "cheque", "direct deposit", "neft", "salary account", "paid directly", "बैंक", "बैंक खाते", "खाते में"],
        })
        if income_mode:
            extracted["income_mode"] = income_mode

        tenure_matches = list(re.finditer(r"(\d+)\s*(?:years?|yrs?|saal|साल|वर्ष)\b", t))
        if tenure_matches:
            extracted["tenure_years"] = int(tenure_matches[-1].group(1))

        return extracted

    def process_turn(self, user_text: str, context: Optional[Dict[str, Any]] = None) -> Tuple[str, QualificationState]:
        """
        Core conversational transition step.
        """
        self.state.history.append({"speaker": "customer", "text": user_text})
        extracted = self.extract_entities(user_text)
        previous_stage = self.state.current_stage
        t = user_text.lower().strip()
        pending_question_before_turn = (
            self.state.get_first_missing_question_key()
            if self.state.current_stage == Stage.QUALIFICATION
            else None
        )

        customer_name = (self.config.customer_name if self.config else "valued customer")
        agent_name = (self.config.agent_name if self.config else "Aisha")
        company_name = (self.config.company_name if self.config else "Home Credit")
        agent_is_female = not self.config or self.config.agent_gender.lower() == "female"
        agent_self_reference = "बोल रही हूँ" if agent_is_female else "बोल रहा हूँ"
        agent_understands = "समझती हूँ" if agent_is_female else "समझता हूँ"
        agent_is_sending = "भेज रही हूँ" if agent_is_female else "भेज रहा हूँ"
        agent_wants = "चाहती" if agent_is_female else "चाहता"
        agent_got_it = "समझ गई" if agent_is_female else "समझ गया"
        wrong_person_while_verifying = (
            self.state.current_stage == Stage.VERIFY_CUSTOMER
            and self._is_wrong_person_utterance(t, customer_name)
        )

        if extracted.get("transfer_intent") and not wrong_person_while_verifying:
            transfer_msg = self._transfer_reply(customer_name, company_name, extracted["transfer_intent"])
            self.state.history.append({"speaker": "agent", "text": transfer_msg})
            return transfer_msg, self.state
        if self.state.current_stage not in {Stage.INITIAL, Stage.VERIFY_CUSTOMER}:
            self._record_extracted_entities(extracted)
            failure = self._eligibility_failure()
            if failure:
                disqualify_msg = self._disqualification_reply(failure, customer_name, company_name)
                self.state.history.append({"speaker": "agent", "text": disqualify_msg})
                return disqualify_msg, self.state

        asks_about_rate = self._contains_non_negated_phrase(t, [
            "interest rate", "interest rates", "roi", "biyaj", "what rate", "what's the rate", "what is the rate", "rate of interest",
            "ब्याज दर", "दर क्या है",
        ])
        if asks_about_rate:
            response_prefix = self._localized(
                "Our interest rates are customized based on property valuation and your profile. "
                "Our Senior Loan Expert will provide the exact interest rate during your direct consultation right after this quick check. ",
                "ब्याज दर संपत्ति के मूल्य और आपकी जानकारी के अनुसार तय होती है। शुरुआती जाँच के बाद वरिष्ठ ऋण विशेषज्ञ से आपको सटीक ब्याज दर की जानकारी मिलेगी। ",
            )
        else:
            response_prefix = ""

        rag_deflection = ""
        asks_product_question = self._contains_non_negated_phrase(t, [
            "processing fee", "fee", "fees", "charges", "cost", "processing time", "doorstep", "verification",
            "how much time", "how long", "branch", "offer details", "product details", "what is the process",
            "शुल्क", "फीस", "घर पर सत्यापन", "कितना समय", "शाखा", "ऑफर की जानकारी",
        ])
        if asks_product_question:
            product_context = (context or {}).get("product_context", "").strip()
            context_is_hindi = bool(re.search(r"[\u0900-\u097f]", product_context))
            use_context = product_context and (
                (self._localized("English", "Hindi") == "Hindi" and context_is_hindi)
                or (self._localized("English", "Hindi") == "English" and not context_is_hindi)
            )
            if use_context:
                rag_deflection = self._localized(
                    f"Here is the available product information: {product_context}. ",
                    f"उपलब्ध उत्पाद जानकारी यह है: {product_context}। ",
                )
            else:
                rag_deflection = self._localized(
                    "I don't have confirmed details about that in the offer information available to me. A senior loan expert can clarify it. ",
                    "उपलब्ध प्रस्ताव जानकारी में इस बारे में पुष्ट विवरण नहीं है। वरिष्ठ ऋण विशेषज्ञ आपको इसकी जानकारी दे सकते हैं। ",
                )

        if self.state.current_stage == Stage.BUSY_CALLBACK_PENDING:
            callback_time = self._extract_callback_time(t)
            if not callback_time and t.strip() in {"later", "anytime", "whenever", "बाद में", "जब भी"}:
                callback_time = user_text.strip()
            if not callback_time:
                clarification = self._localized(
                    "What date and time would be convenient for our callback?",
                    "दोबारा फ़ोन करने के लिए कौन-सी तारीख़ और समय सुविधाजनक रहेगा?",
                )
                self.state.history.append({"speaker": "agent", "text": clarification})
                return clarification, self.state
            self.state.callback_time = callback_time
            self.state.current_stage = Stage.BUSY_CALLBACK
            farewell = self._localized(
                f"Thank you, {customer_name}. I have noted your preferred callback time as {callback_time}. Our representative will contact you then. Have a good day!",
                f"धन्यवाद, {customer_name} जी। मैंने {callback_time} पर दोबारा फ़ोन करने का समय नोट कर लिया है। हमारी टीम आपसे तब संपर्क करेगी। आपका दिन शुभ हो।",
            )
            self.state.history.append({"speaker": "agent", "text": farewell})
            return farewell, self.state

        if extracted.get("is_busy") and not wrong_person_while_verifying:
            self.state.customer_verified = True
            self.state.is_busy = True
            self.state.callback_time = extracted.get("callback_time", "later")
            has_callback_time = self.state.callback_time != "later"
            self.state.current_stage = Stage.BUSY_CALLBACK if has_callback_time else Stage.BUSY_CALLBACK_PENDING
            farewell = self._localized(
                (
                    f"I completely understand, {customer_name}. What would be a convenient date and time for us to call you back?"
                    if not has_callback_time else
                    f"Thank you, {customer_name}. I have noted your preferred callback time for {extracted.get('callback_time')}. Our representative will reach out then. Have a wonderful day!"
                ),
                (
                    f"मैं {agent_understands}, {customer_name} जी। आपको दोबारा किस तारीख़ और समय पर फ़ोन करना सुविधाजनक रहेगा?"
                    if not has_callback_time else
                    f"धन्यवाद, {customer_name} जी। मैंने {extracted.get('callback_time')} पर दोबारा फ़ोन करने का समय नोट कर लिया है। हमारी टीम आपसे तब संपर्क करेगी। आपका दिन शुभ हो।"
                ),
            )
            self.state.history.append({"speaker": "agent", "text": farewell})
            return farewell, self.state

        if self.state.current_stage == Stage.INITIAL:
            self.state.current_stage = Stage.VERIFY_CUSTOMER
            greeting = self._localized(
                f"Hello, am I speaking with {customer_name}?",
                f"नमस्ते, क्या मेरी बात {customer_name} जी से हो रही है?",
            )
            self.state.history.append({"speaker": "agent", "text": greeting})
            return greeting, self.state

        if self.state.current_stage == Stage.VERIFY_CUSTOMER:
            customer_first_name = customer_name.lower().split()[0] if customer_name.split() else ""
            name_pattern = re.escape(customer_first_name)
            identity_match = bool(re.search(
                rf"\b(?:i am|i'm|this is|my name is)\s+{name_pattern}\b|\b{name_pattern}\s+(?:here|speaking)\b",
                t,
            )) if name_pattern else False
            wrong_person = self._is_wrong_person_utterance(t, customer_name)
            if wrong_person:
                self.state.customer_verified = False
                self.state.current_stage = Stage.CALL_ENDED
                apology = "चाहती" if agent_is_female else "चाहता"
                farewell = self._localized(
                    f"I apologize for the inconvenience. Thank you for your time with {company_name}. Have a good day!",
                    f"असुविधा के लिए क्षमा {apology} हूँ। {company_name} को अपना समय देने के लिए धन्यवाद। आपका दिन शुभ हो।",
                )
                self.state.history.append({"speaker": "agent", "text": farewell})
                return farewell, self.state

            if identity_match or any(w in t for w in ["yes", "speaking", "this is", "myself", "yeah", "correct", "हाँ", "हां", "जी", "बिल्कुल", "सही है", "मैं ही"]):
                self.state.customer_verified = True
                self.state.current_stage = Stage.OFFER_PITCH
                self._record_extracted_entities(extracted)

                if extracted.get("transfer_intent"):
                    transfer_msg = self._transfer_reply(customer_name, company_name, extracted["transfer_intent"])
                    self.state.history.append({"speaker": "agent", "text": transfer_msg})
                    return transfer_msg, self.state

                failure = self._eligibility_failure()
                if failure:
                    disqualify_msg = self._disqualification_reply(failure, customer_name, company_name)
                    self.state.history.append({"speaker": "agent", "text": disqualify_msg})
                    return disqualify_msg, self.state

                requested_amount = extracted.get("loan_amount")
                over_limit = requested_amount is not None and requested_amount > 7500000
                if requested_amount is not None and not over_limit:
                    self.state.loan_amount = requested_amount

                pitch = self._localized(
                    (
                        f"Hello {customer_name}! I am {agent_name} calling from {company_name}. "
                        f"We are reaching out to reward your loyalty with a pre-approved Loan Against Property offer of up to ₹75 Lakhs. "
                        f"Do you have two minutes to check your preliminary eligibility?"
                    ),
                    (
                        f"नमस्ते {customer_name} जी! मैं {agent_name}, {company_name} से {agent_self_reference}। "
                        f"हमारे मूल्यवान ग्राहक होने के नाते हम आपको ₹75 लाख तक के संपत्ति के बदले ऋण के विशेष पूर्व-मंज़ूर प्रस्ताव के बारे में बता रहे हैं। "
                        f"क्या आप अपनी शुरुआती पात्रता जाँचने के लिए दो मिनट दे सकेंगे?"
                    ),
                )
                if over_limit:
                    self.state.pending_loan_amount_negotiation = requested_amount
                    self.state.loan_amount = None
                    self.state.current_stage = Stage.NEGOTIATING_LOAN_AMOUNT
                    pitch += self._localized(
                        " Your requested amount is above the offer limit of ₹75 Lakhs. Would you like to continue with ₹75 Lakhs?",
                        " आपकी बताई राशि ₹75 लाख की सीमा से अधिक है। क्या आप ₹75 लाख के साथ आगे बढ़ना चाहेंगे?",
                    )
                self.state.history.append({"speaker": "agent", "text": pitch})
                return pitch, self.state
            elif "who is calling" in t or "kaha se" in t or "कौन बोल" in t or "कहाँ से" in t or "कहां से" in t:
                rep = self._localized(
                    f"I am {agent_name} from {company_name}. May I confirm if I am speaking with {customer_name}?",
                    f"मैं {agent_name}, {company_name} से {agent_self_reference}। क्या मेरी बात {customer_name} जी से हो रही है?",
                )
                self.state.history.append({"speaker": "agent", "text": rep})
                return rep, self.state
            else:
                repeat = self._localized(
                    f"I am calling for {customer_name}. May I confirm that I am speaking with them?",
                    f"मैं {customer_name} जी से बात करना {agent_wants} हूँ। क्या आप पुष्टि कर सकते हैं कि आप वही हैं?",
                )
                self.state.history.append({"speaker": "agent", "text": repeat})
                return repeat, self.state

        if extracted.get("transfer_intent") or self.state.transfer_intent:
            transfer_msg = self._transfer_reply(
                customer_name,
                company_name,
                extracted.get("transfer_intent") or self.state.transfer_intent,
            )
            self.state.history.append({"speaker": "agent", "text": transfer_msg})
            return transfer_msg, self.state

        if self.state.current_stage == Stage.OFFER_PITCH:
            self._record_extracted_entities(extracted)
            failure = self._eligibility_failure()
            if failure:
                disqualify_msg = self._disqualification_reply(failure, customer_name, company_name)
                self.state.history.append({"speaker": "agent", "text": disqualify_msg})
                return disqualify_msg, self.state

            volunteered_eligibility_detail = any(key in extracted for key in (
                "property_type", "ownership_status", "documents_available", "loan_amount",
                "occupation", "income_mode", "market_value", "tenure_years",
            ))
            offer_intent = self._latest_choice(t, {
                True: ["yes", "sure", "okay", "ok", "please", "proceed", "go ahead", "interested", "हाँ", "हां", "जी", "ठीक है", "आगे बढ़ें", "बताइए", "चलिए"],
                False: ["not interested", "don't want", "do not want", "no thanks", "no", "nope", "नहीं चाहिए", "रुचि नहीं", "नहीं"],
            })
            accepted_offer = offer_intent is True or (offer_intent is None and volunteered_eligibility_detail) or asks_about_rate
            declined_offer = offer_intent is False

            if declined_offer:
                self.state.current_stage = Stage.CALL_ENDED
                farewell = self._localized(
                    f"Understood, {customer_name}. Thank you for your time with {company_name}. Have a good day!",
                    f"{agent_got_it}, {customer_name} जी। {company_name} को अपना समय देने के लिए धन्यवाद। आपका दिन शुभ हो।",
                )
                self.state.history.append({"speaker": "agent", "text": farewell})
                return farewell, self.state

            if not accepted_offer:
                confirmation = self._localized(
                    f"{response_prefix}{rag_deflection}Would you like me to continue with the preliminary eligibility check?",
                    f"{response_prefix}{rag_deflection}क्या मैं शुरुआती पात्रता जाँच आगे बढ़ाऊँ?",
                )
                self.state.history.append({"speaker": "agent", "text": confirmation})
                return confirmation, self.state

            self.state.current_stage = Stage.QUALIFICATION

        negotiating_amount = self.state.current_stage == Stage.NEGOTIATING_LOAN_AMOUNT

        first_missing_before = pending_question_before_turn
        if self.state.current_stage == Stage.QUALIFICATION and first_missing_before:
            if first_missing_before == "property_type" and not self.state.property_type and "property_type" not in extracted:
                if any(w in t for w in ["flat", "house", "apartment", "makan"]):
                    extracted["property_type"] = PropertyType.RESIDENTIAL.value
                elif any(w in t for w in ["shop", "office", "store", "dukan"]):
                    extracted["property_type"] = PropertyType.COMMERCIAL.value
                elif any(w in t for w in ["factory", "warehouse", "shed"]):
                    extracted["property_type"] = PropertyType.INDUSTRIAL.value
                elif any(w in t for w in ["agri", "farm", "khet", "kheti"]):
                    extracted["property_type"] = PropertyType.AGRICULTURAL.value

            elif first_missing_before == "ownership_status" and not self.state.ownership_status and "ownership_status" not in extracted:
                if any(w in t for w in ["sole", "single", "only me", "my name", "alone"]) or re.search(r"\bown\b", t):
                    extracted["ownership_status"] = OwnershipStatus.SOLE.value
                elif any(w in t for w in ["joint", "jointly", "partner", "wife", "brother", "family"]):
                    extracted["ownership_status"] = OwnershipStatus.JOINT.value

            elif first_missing_before == "documents_available" and self.state.documents_available is None and "documents_available" not in extracted:
                if any(w in t for w in ["yes", "available", "ready", "have them", "have it", "have papers", "have documents", "at home", "with me", "haan"]):
                    if any(w in t for w in ["photocopy", "xerox", "lost", "missing", "don't have", "no", "nahi"]):
                        extracted["documents_available"] = False
                    else:
                        extracted["documents_available"] = True
                elif any(w in t for w in ["no", "photocopy", "xerox", "lost", "missing", "copies", "nahi"]):
                    extracted["documents_available"] = False

            elif first_missing_before == "market_value" and not self.state.market_value and "market_value" not in extracted:
                val_m = re.search(r"(\d+(?:\.\d+)?)\s*(crore|crores|cr|lakh|lakhs|lacs|lac)?", t)
                if val_m:
                    n = float(val_m.group(1))
                    u = val_m.group(2) or ""
                    if "cr" in u or "crore" in u:
                        extracted["market_value"] = f"₹{n} Crore"
                    elif "lakh" in u or "lac" in u:
                        extracted["market_value"] = f"₹{n} Lakhs"
                    else:
                        extracted["market_value"] = f"₹{n:,.0f}"

            elif first_missing_before == "tenure" and self.state.tenure_years is None and "tenure_years" not in extracted:
                ten_m = re.search(r"(\d+)", t)
                if ten_m:
                    extracted["tenure_years"] = int(ten_m.group(1))

        self._record_extracted_entities(extracted)
        failure = self._eligibility_failure()
        if failure:
            disqualify_msg = self._disqualification_reply(failure, customer_name, company_name)
            self.state.history.append({"speaker": "agent", "text": disqualify_msg})
            return disqualify_msg, self.state

        requested_amount = extracted.get("loan_amount")
        negotiation_intent = self._latest_choice(t, {
            True: ["yes", "okay", "ok", "sure", "fine", "proceed", "agree", "75", "75 lakhs", "can do", "will do", "is enough", "works for me", "settle for", "हाँ", "हां", "जी", "ठीक है", "मंज़ूर", "मंजूर", "आगे बढ़ें"],
            False: ["no thanks", "no", "nope", "decline", "cannot", "can't", "नहीं", "मना"],
        })
        explicitly_requests_lower_amount = self._contains_non_negated_phrase(t, [
            "need", "want", "looking for", "require", "borrow", "loan of", "can do", "will do", "settle for",
            "चाहिए", "राशि", "लोन लेना है",
        ])
        if negotiating_amount:
            if requested_amount is not None and requested_amount <= 7500000 and (negotiation_intent is not False or explicitly_requests_lower_amount):
                self.state.loan_amount = requested_amount
                self.state.pending_loan_amount_negotiation = None
                self.state.current_stage = Stage.QUALIFICATION
            elif negotiation_intent is True:
                self.state.loan_amount = 7500000
                self.state.pending_loan_amount_negotiation = None
                self.state.current_stage = Stage.QUALIFICATION
            elif negotiation_intent is False:
                self.state.disqualified = True
                self.state.disqualification_reason = "Customer declined to proceed within the maximum offer limit of ₹75 Lakhs."
                self.state.current_stage = Stage.DISQUALIFIED
                msg = self._localized(
                    f"I understand, {customer_name}. The maximum offer is ₹75 Lakhs, so we cannot proceed with the higher amount. Thank you for your time with {company_name}.",
                    f"मैं {agent_understands}, {customer_name} जी। अधिकतम प्रस्ताव ₹75 लाख का है, इसलिए इससे अधिक राशि के लिए हम आगे नहीं बढ़ सकते। {company_name} को अपना समय देने के लिए धन्यवाद।",
                )
                self.state.history.append({"speaker": "agent", "text": msg})
                return msg, self.state
            else:
                msg = self._localized(
                    f"The offer is limited to ₹75 Lakhs. Would you like to continue with ₹75 Lakhs?",
                    "यह प्रस्ताव अधिकतम ₹75 लाख तक है। क्या आप ₹75 लाख के साथ आगे बढ़ना चाहेंगे?",
                )
                self.state.history.append({"speaker": "agent", "text": msg})
                return msg, self.state
        elif requested_amount is not None and requested_amount > 7500000:
            self.state.pending_loan_amount_negotiation = requested_amount
            self.state.loan_amount = None
            self.state.current_stage = Stage.NEGOTIATING_LOAN_AMOUNT
            msg = self._localized(
                f"{response_prefix}{rag_deflection}Our current offer is available for up to ₹75 Lakhs. Would you like to proceed with the maximum amount of ₹75 Lakhs?",
                f"{response_prefix}{rag_deflection}हमारा मौजूदा प्रस्ताव अधिकतम ₹75 लाख तक है। क्या आप ₹75 लाख के साथ आगे बढ़ना चाहेंगे?",
            ).strip()
            self.state.history.append({"speaker": "agent", "text": msg})
            return msg, self.state
        elif requested_amount is not None:
            self.state.loan_amount = requested_amount

        if self.state.is_checklist_complete():
            self.state.qualified = True
            self.state.current_stage = Stage.QUALIFIED_HANDOFF
            handoff_msg = self._localized(
                (
                    f"{response_prefix}Congratulations, {customer_name}! Based on your details, you have successfully qualified for our "
                    f"Loan Against Property offer of ₹{self.state.loan_amount:,.0f}. I am handing over your profile to our Senior Loan Expert, "
                    f"who will call you shortly to discuss exact interest rates, sanction letter, and doorstep verification. "
                    f"Thank you for being a valued customer of {company_name}, and have a wonderful day!"
                ),
                (
                    f"बधाई हो, {customer_name} जी! दी गई जानकारी के आधार पर आप ₹{self.state.loan_amount:,.0f} के संपत्ति ऋण प्रस्ताव की शुरुआती पात्रता में सफल रहे हैं। "
                    f"मैं आपकी जानकारी वरिष्ठ ऋण विशेषज्ञ को {agent_is_sending}। वे सटीक ब्याज दर, मंज़ूरी और दस्तावेज़ सत्यापन की जानकारी देने के लिए जल्द आपसे संपर्क करेंगे। "
                    f"{company_name} के मूल्यवान ग्राहक होने के लिए धन्यवाद। आपका दिन शुभ हो।"
                ),
            ).strip()
            self.state.history.append({"speaker": "agent", "text": handoff_msg})
            return handoff_msg, self.state

        self.state.current_stage = Stage.QUALIFICATION
        first_missing = self.state.get_first_missing_question_key()

        if self._localized("English", "Hindi") == "Hindi":
            question_map = {
                "property_type": "कृपया बताइए, आपकी संपत्ति आवासीय है, व्यावसायिक है या औद्योगिक?",
                "ownership_status": "क्या संपत्ति केवल आपके नाम पर है या परिवार के किसी सदस्य के साथ संयुक्त रूप से है?",
                "documents_available": "क्या सत्यापन के लिए संपत्ति के मूल दस्तावेज़ उपलब्ध हैं?",
                "loan_amount": "आप कितनी ऋण राशि लेना चाहते हैं?",
                "occupation_and_income": (
                    "कृपया अपना काम बताइए। क्या आप नौकरी करते हैं या अपना व्यवसाय चलाते हैं, और आपकी आय बैंक खाते में आती है या नकद मिलती है?"
                    if self.state.occupation is None and self.state.income_mode is None else
                    "क्या आपकी आय सीधे बैंक खाते में आती है या नकद मिलती है?"
                    if self.state.income_mode is None else
                    "कृपया पुष्टि करें, आप नौकरी करते हैं या अपना व्यवसाय चलाते हैं?"
                ),
                "market_value": "आपकी संपत्ति का अनुमानित मौजूदा बाज़ार मूल्य कितना है?",
                "tenure": "आप ऋण कितने साल में चुकाना चाहेंगे? इस योजना में अवधि 3 से 15 साल तक हो सकती है।",
            }
        else:
            question_map = {
                "property_type": "Could you please tell me if your property is Residential, Commercial, or Industrial?",
                "ownership_status": "Is the property solely in your name, or is it jointly owned with a family member or partner?",
                "documents_available": "Do you have the original property documents available for physical verification?",
                "loan_amount": "How much loan amount are you looking to borrow?",
                "occupation_and_income": (
                    "Could you tell me your occupation (Salaried or Self-Employed), and is your income received through the bank or in cash?"
                    if self.state.occupation is None and self.state.income_mode is None else
                    "Is your income received directly in your bank account or in cash?"
                    if self.state.income_mode is None else
                    "Could you please confirm if you are Salaried or Self-Employed?"
                ),
                "market_value": "Approximately what is the estimated current market value of your property?",
                "tenure": "How many years would you like to choose for the loan repayment tenure (between 3 and 15 years)?",
            }

        next_question = question_map.get(first_missing, "Could you provide more details regarding your property?")
        final_reply = f"{response_prefix}{rag_deflection}{next_question}".strip()
        self.state.history.append({"speaker": "agent", "text": final_reply})
        return final_reply, self.state

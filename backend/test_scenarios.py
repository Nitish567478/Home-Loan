import sys
from pathlib import Path
from typing import List, Dict, Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.agent import VoiceAgent
from app.config import AgentConfig
from app.state_machine import Stage, PropertyType, OwnershipStatus, IncomeMode

def run_all_evaluation_tests() -> Dict[str, Any]:
    """
    Executes the complete test matrix covering all 12+ scenarios required by the spec.
    Returns structured results with pass/fail validation.
    """
    test_cases = [
        {
            "id": "TEST-01",
            "name": "Happy Path: Perfect Eligible Customer",
            "description": "Customer answers all 7 questions meeting all criteria -> Handoff to Senior Expert.",
            "conversation": [
                ("", Stage.VERIFY_CUSTOMER),
                ("Yes, speaking.", Stage.OFFER_PITCH),
                ("Yes, sure, let's check.", Stage.QUALIFICATION),
                ("It is a residential apartment.", Stage.QUALIFICATION),
                ("It is solely owned by me.", Stage.QUALIFICATION),
                ("Yes, I have original property documents at home.", Stage.QUALIFICATION),
                ("I am looking for a loan of 50 lakhs.", Stage.QUALIFICATION),
                ("I am salaried in an IT firm and get paid directly in my bank account.", Stage.QUALIFICATION),
                ("The market value is around 1 crore.", Stage.QUALIFICATION),
                ("I would like a 10 years repayment tenure.", Stage.QUALIFIED_HANDOFF)
            ],
            "expected_stage": Stage.QUALIFIED_HANDOFF,
            "expected_qualified": True
        },
        {
            "id": "TEST-02",
            "name": "Immediate Disqualification: Agricultural Land",
            "description": "Customer mentions agricultural property -> Immediate rejection without asking further questions.",
            "conversation": [
                ("", Stage.VERIFY_CUSTOMER),
                ("Yes, this is Rahul.", Stage.OFFER_PITCH),
                ("Sure, go ahead.", Stage.QUALIFICATION),
                ("It is agricultural farmland in Haryana.", Stage.DISQUALIFIED)
            ],
            "expected_stage": Stage.DISQUALIFIED,
            "expected_disqualified": True
        },
        {
            "id": "TEST-03",
            "name": "Immediate Disqualification: Cash Income",
            "description": "Customer is self-employed but receives income in cash -> Immediate disqualification.",
            "conversation": [
                ("", Stage.VERIFY_CUSTOMER),
                ("Yes, speaking.", Stage.OFFER_PITCH),
                ("Yes, please.", Stage.QUALIFICATION),
                ("Residential property.", Stage.QUALIFICATION),
                ("Sole ownership.", Stage.QUALIFICATION),
                ("Yes, original papers are with me.", Stage.QUALIFICATION),
                ("40 lakhs.", Stage.QUALIFICATION),
                ("I run a retail shop and take all payments in cash.", Stage.DISQUALIFIED)
            ],
            "expected_stage": Stage.DISQUALIFIED,
            "expected_disqualified": True
        },
        {
            "id": "TEST-04",
            "name": "Immediate Disqualification: Missing Original Documents",
            "description": "Customer has only photocopies / xerox -> Immediate rejection.",
            "conversation": [
                ("", Stage.VERIFY_CUSTOMER),
                ("Yes, Rahul speaking.", Stage.OFFER_PITCH),
                ("Sure.", Stage.QUALIFICATION),
                ("Commercial shop.", Stage.QUALIFICATION),
                ("Joint ownership with my brother.", Stage.QUALIFICATION),
                ("I only have photocopies, original papers are lost.", Stage.DISQUALIFIED)
            ],
            "expected_stage": Stage.DISQUALIFIED,
            "expected_disqualified": True
        },
        {
            "id": "TEST-05",
            "name": "Immediate Disqualification: Tenure Too Short (< 3 Years)",
            "description": "Customer requests 2 years repayment tenure -> Disqualification.",
            "conversation": [
                ("", Stage.VERIFY_CUSTOMER),
                ("Yes.", Stage.OFFER_PITCH),
                ("Okay, ask.", Stage.QUALIFICATION),
                ("Residential flat.", Stage.QUALIFICATION),
                ("Solely in my name.", Stage.QUALIFICATION),
                ("Yes, original papers available.", Stage.QUALIFICATION),
                ("30 lakhs.", Stage.QUALIFICATION),
                ("Salaried, bank deposit.", Stage.QUALIFICATION),
                ("80 lakhs market value.", Stage.QUALIFICATION),
                ("I want to finish in 2 years.", Stage.DISQUALIFIED)
            ],
            "expected_stage": Stage.DISQUALIFIED,
            "expected_disqualified": True
        },
        {
            "id": "TEST-06",
            "name": "Immediate Disqualification: Tenure Too Long (> 15 Years)",
            "description": "Customer requests 20 years repayment tenure -> Disqualification.",
            "conversation": [
                ("", Stage.VERIFY_CUSTOMER),
                ("Yes.", Stage.OFFER_PITCH),
                ("Okay.", Stage.QUALIFICATION),
                ("Residential.", Stage.QUALIFICATION),
                ("Sole.", Stage.QUALIFICATION),
                ("Yes, original docs ready.", Stage.QUALIFICATION),
                ("50 lakhs.", Stage.QUALIFICATION),
                ("Salaried with bank salary.", Stage.QUALIFICATION),
                ("1.5 crore.", Stage.QUALIFICATION),
                ("I want a 20 years loan.", Stage.DISQUALIFIED)
            ],
            "expected_stage": Stage.DISQUALIFIED,
            "expected_disqualified": True
        },
        {
            "id": "TEST-07",
            "name": "Loan Limit Renegotiation (> Rs. 75 Lakhs)",
            "description": "Customer asks for 90 Lakhs -> Agent offers max Rs. 75L -> Customer accepts -> Continues to qualify.",
            "conversation": [
                ("", Stage.VERIFY_CUSTOMER),
                ("Yes, speaking.", Stage.OFFER_PITCH),
                ("Yes.", Stage.QUALIFICATION),
                ("Residential house.", Stage.QUALIFICATION),
                ("Sole ownership.", Stage.QUALIFICATION),
                ("Original documents are available.", Stage.QUALIFICATION),
                ("I need 90 lakhs.", Stage.NEGOTIATING_LOAN_AMOUNT),
                ("Yes, I agree to proceed with 75 lakhs.", Stage.QUALIFICATION),
                ("Salaried with salary in bank.", Stage.QUALIFICATION),
                ("Market value is 2 crore.", Stage.QUALIFICATION),
                ("15 years tenure.", Stage.QUALIFIED_HANDOFF)
            ],
            "expected_stage": Stage.QUALIFIED_HANDOFF,
            "expected_qualified": True
        },
        {
            "id": "TEST-08",
            "name": "Joint Ownership Verification",
            "description": "Joint ownership property is recognized as eligible and continues qualification.",
            "conversation": [
                ("", Stage.VERIFY_CUSTOMER),
                ("Yes, Rahul here.", Stage.OFFER_PITCH),
                ("Sure.", Stage.QUALIFICATION),
                ("Commercial office.", Stage.QUALIFICATION),
                ("It is jointly owned with my business partner.", Stage.QUALIFICATION)
            ],
            "expected_stage": Stage.QUALIFICATION,
            "check_ownership": "Joint"
        },
        {
            "id": "TEST-09",
            "name": "Existing Loan on Property -> Transfer Specialist Switch",
            "description": "Customer mentions active mortgage/loan on property -> Handed off to loan transfer specialist.",
            "conversation": [
                ("", Stage.VERIFY_CUSTOMER),
                ("Yes, speaking.", Stage.OFFER_PITCH),
                ("Actually, I already have a loan running on this property.", Stage.TRANSFERRED_SPECIALIST)
            ],
            "expected_stage": Stage.TRANSFERRED_SPECIALIST,
            "expected_transferred": True
        },
        {
            "id": "TEST-10",
            "name": "EMI Reduction Request -> Transfer Specialist Switch",
            "description": "Customer asks to reduce their current EMI -> Handed off to balance transfer specialist.",
            "conversation": [
                ("", Stage.VERIFY_CUSTOMER),
                ("Yes, this is Rahul.", Stage.OFFER_PITCH),
                ("Can you help reduce my current EMI on my existing loan?", Stage.TRANSFERRED_SPECIALIST)
            ],
            "expected_stage": Stage.TRANSFERRED_SPECIALIST,
            "expected_transferred": True
        },
        {
            "id": "TEST-11",
            "name": "Out-of-Order Multi-Entity Extraction",
            "description": "Customer answers property type, market value, ownership, and loan amount in one turn -> Agent captures all 4 and asks only next missing question.",
            "conversation": [
                ("", Stage.VERIFY_CUSTOMER),
                ("Yes, speaking.", Stage.OFFER_PITCH),
                ("Sure.", Stage.QUALIFICATION),
                ("I have a residential house worth about 1.2 crore jointly owned with my wife and I need 40 lakhs.", Stage.QUALIFICATION)
            ],
            "expected_stage": Stage.QUALIFICATION,
            "check_fields": {
                "property_type": "Residential",
                "ownership_status": "Joint",
                "market_value": "₹1.2 Crore",
                "loan_amount": 4000000,
                "next_missing": "documents_available"
            }
        },
        {
            "id": "TEST-12",
            "name": "Busy Customer Callback Scheduling",
            "description": "Customer says they are in a meeting -> Agent asks/records callback time and gracefully ends call.",
            "conversation": [
                ("", Stage.VERIFY_CUSTOMER),
                ("Yes, speaking, but I am in a meeting right now, please call me tomorrow at 4 pm.", Stage.BUSY_CALLBACK)
            ],
            "expected_stage": Stage.BUSY_CALLBACK,
            "expected_busy": True
        },
        {
            "id": "TEST-13",
            "name": "Adversarial Contradiction Handling",
            "description": "Customer says 'Residential... actually no, it is agricultural land' -> Latest answer (Agricultural) triggers disqualification.",
            "conversation": [
                ("", Stage.VERIFY_CUSTOMER),
                ("Yes, speaking.", Stage.OFFER_PITCH),
                ("Sure.", Stage.QUALIFICATION),
                ("It is residential... wait, actually it is agricultural farmland.", Stage.DISQUALIFIED)
            ],
            "expected_stage": Stage.DISQUALIFIED,
            "expected_disqualified": True
        },
        {
            "id": "TEST-14",
            "name": "Diversion / Interest Rate Deflection",
            "description": "Customer interrupts asking for interest rate -> Agent defers rate to Senior Expert and resumes checklist.",
            "conversation": [
                ("", Stage.VERIFY_CUSTOMER),
                ("Yes.", Stage.OFFER_PITCH),
                ("Wait, what is your exact interest rate?", Stage.QUALIFICATION)
            ],
            "expected_stage": Stage.QUALIFICATION
        }
    ]

    results = []
    total_passed = 0

    for tc in test_cases:
        agent = VoiceAgent()
        transcript = []
        passed = True
        failure_msg = ""

        try:
            for utterance, expected_turn_stage in tc["conversation"]:
                reply_data = agent.process_customer_turn(utterance)
                transcript.append({
                    "user": utterance or "[Agent Initial Call]",
                    "agent": reply_data["agent_reply"],
                    "stage": reply_data["state"]["current_stage"]
                })

            final_state = agent.state_machine.state
            
            if "expected_stage" in tc and final_state.current_stage != tc["expected_stage"]:
                passed = False
                failure_msg += f"Expected stage {tc['expected_stage']}, got {final_state.current_stage}. "

            if tc.get("expected_qualified") and not final_state.qualified:
                passed = False
                failure_msg += "Expected state.qualified to be True. "

            if tc.get("expected_disqualified") and not final_state.disqualified:
                passed = False
                failure_msg += "Expected state.disqualified to be True. "

            if tc.get("expected_transferred") and not final_state.transferred:
                passed = False
                failure_msg += "Expected state.transferred to be True. "

            if tc.get("expected_busy") and not final_state.is_busy:
                passed = False
                failure_msg += "Expected state.is_busy to be True. "

            if "check_ownership" in tc and final_state.ownership_status != tc["check_ownership"]:
                passed = False
                failure_msg += f"Expected ownership {tc['check_ownership']}, got {final_state.ownership_status}. "

            if "check_fields" in tc:
                cf = tc["check_fields"]
                if "property_type" in cf and final_state.property_type != cf["property_type"]:
                    passed = False
                    failure_msg += f"Expected property_type {cf['property_type']}, got {final_state.property_type}. "
                if "ownership_status" in cf and final_state.ownership_status != cf["ownership_status"]:
                    passed = False
                    failure_msg += f"Expected ownership_status {cf['ownership_status']}, got {final_state.ownership_status}. "
                if "loan_amount" in cf and final_state.loan_amount != cf["loan_amount"]:
                    passed = False
                    failure_msg += f"Expected loan_amount {cf['loan_amount']}, got {final_state.loan_amount}. "
                if "next_missing" in cf:
                    first_missing = final_state.get_first_missing_question_key()
                    if first_missing != cf["next_missing"]:
                        passed = False
                        failure_msg += f"Expected next missing '{cf['next_missing']}', got '{first_missing}'. "

        except Exception as e:
            passed = False
            failure_msg = f"Exception during execution: {str(e)}"

        if passed:
            total_passed += 1

        results.append({
            "id": tc["id"],
            "name": tc["name"],
            "description": tc["description"],
            "passed": passed,
            "failure_reason": failure_msg if not passed else None,
            "transcript": transcript,
            "final_state": final_state.to_dict()
        })

    return {
        "total_tests": len(test_cases),
        "total_passed": total_passed,
        "pass_rate": f"{(total_passed / len(test_cases)) * 100:.1f}%",
        "results": results
    }

if __name__ == "__main__":
    print("=" * 70)
    print("RUNNING HOME CREDIT LAP VOICE AGENT TEST SUITE")
    print("=" * 70)
    summary = run_all_evaluation_tests()
    for res in summary["results"]:
        status = "[PASS]" if res["passed"] else "[FAIL]"
        print(f"{status} | {res['id']}: {res['name']}")
        if not res["passed"]:
            print(f"     Reason: {res['failure_reason']}")
    print("-" * 70)
    print(f"RESULTS: {summary['total_passed']}/{summary['total_tests']} tests passed ({summary['pass_rate']})")
    print("=" * 70)

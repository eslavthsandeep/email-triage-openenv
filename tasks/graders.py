# """
# graders.py — Programmatic graders for each task.

# Each grader takes the final environment state (from env.state()) and returns
# a score in [0.0, 1.0] with a breakdown dict.

# Graders are deterministic and have clear success/failure criteria.
# """

# from __future__ import annotations
# from typing import Dict, Any, Tuple

# from env.models import EmailLabel
# from env.data import (
#     MUST_ESCALATE, MUST_SPAM, MUST_NEWSLETTER, REPLY_KEYWORDS
# )


# def grade_task_easy(state: dict) -> Tuple[float, Dict[str, Any]]:
#     """
#     Task Easy: Classify all emails correctly and delete all spam.

#     Scoring:
#     - 70% — Classification accuracy (per-email)
#     - 30% — Spam deleted (per-spam email)
#     """
#     emails = state["emails"]
#     total = len(emails)
#     if total == 0:
#         return 0.0, {"error": "no emails in state"}

#     # Classification accuracy
#     correct_classifications = 0
#     spam_handled = 0
#     spam_total = len(MUST_SPAM)

#     for eid, email in emails.items():
#         true_label = email["true_label"]
#         current_label = email["label"].value if hasattr(email["label"], "value") else str(email["label"])

#         # Check classification correctness
#         if current_label == true_label:
#             correct_classifications += 1
#         # Spam deleted = archived with spam label or true_label==spam and archived
#         if eid in MUST_SPAM and current_label in ("archived", "spam"):
#             spam_handled += 1

#     classification_score = correct_classifications / total
#     spam_score = spam_handled / max(spam_total, 1)

#     final_score = 0.70 * classification_score + 0.30 * spam_score

#     breakdown = {
#         "classification_accuracy": round(classification_score, 3),
#         "correct_classifications": correct_classifications,
#         "total_emails": total,
#         "spam_handled": spam_handled,
#         "spam_total": spam_total,
#         "spam_score": round(spam_score, 3),
#         "final_score": round(final_score, 3),
#     }
#     return round(final_score, 3), breakdown


# def grade_task_medium(state: dict) -> Tuple[float, Dict[str, Any]]:
#     """
#     Task Medium: Sort inbox, reply to urgent emails, unsubscribe from newsletters.

#     Scoring:
#     - 40% — Classification accuracy
#     - 35% — Urgent emails replied to (with non-empty content)
#     - 25% — Newsletters unsubscribed / archived
#     """
#     emails = state["emails"]
#     total = len(emails)

#     correct_classifications = 0
#     urgent_replied = 0
#     urgent_total = 0
#     newsletters_handled = 0
#     newsletter_total = len(MUST_NEWSLETTER)

#     for eid, email in emails.items():
#         true_label = email["true_label"]
#         current_label = email["label"].value if hasattr(email["label"], "value") else str(email["label"])

#         if current_label == true_label or (true_label == "spam" and current_label == "archived"):
#             correct_classifications += 1

#         if true_label == "urgent":
#             urgent_total += 1
#             if email.get("replied", False):
#                 urgent_replied += 1

#         if eid in MUST_NEWSLETTER and current_label == "archived":
#             newsletters_handled += 1

#     classification_score = correct_classifications / max(total, 1)
#     reply_score = urgent_replied / max(urgent_total, 1)
#     newsletter_score = newsletters_handled / max(newsletter_total, 1)

#     final_score = 0.40 * classification_score + 0.35 * reply_score + 0.25 * newsletter_score

#     breakdown = {
#         "classification_accuracy": round(classification_score, 3),
#         "urgent_replied": urgent_replied,
#         "urgent_total": urgent_total,
#         "reply_score": round(reply_score, 3),
#         "newsletters_handled": newsletters_handled,
#         "newsletter_score": round(newsletter_score, 3),
#         "final_score": round(final_score, 3),
#     }
#     return round(final_score, 3), breakdown


# def grade_task_hard(state: dict) -> Tuple[float, Dict[str, Any]]:
#     """
#     Task Hard: Full triage — classify, reply with quality, escalate critical,
#     archive resolved, and submit a triage summary.

#     Scoring:
#     - 25% — Classification accuracy
#     - 30% — Reply quality (keyword matching for emails requiring replies)
#     - 25% — Critical escalations (MUST_ESCALATE emails)
#     - 10% — Newsletter/spam cleanup
#     - 10% — Summary submitted
#     """
#     emails = state["emails"]
#     total = len(emails)

#     correct_classifications = 0
#     critical_escalated = 0
#     critical_total = len(MUST_ESCALATE)
#     newsletters_cleaned = 0
#     spam_cleaned = 0
#     cleanup_total = len(MUST_NEWSLETTER) + len(MUST_SPAM)

#     # Reply quality — we can't re-score the body post-hoc, so we check if replied
#     # and give partial credit; full scoring happens during step()
#     urgent_reply_score_sum = 0.0
#     urgent_with_replies = 0

#     for eid, email in emails.items():
#         true_label = email["true_label"]
#         current_label = email["label"].value if hasattr(email["label"], "value") else str(email["label"])

#         if current_label == true_label or (true_label == "spam" and current_label == "archived"):
#             correct_classifications += 1

#         if eid in MUST_ESCALATE and email.get("escalated", False):
#             critical_escalated += 1

#         if eid in MUST_NEWSLETTER and current_label == "archived":
#             newsletters_cleaned += 1
#         if eid in MUST_SPAM and current_label == "archived":
#             spam_cleaned += 1

#         # Partial credit for replies on emails that needed them
#         if eid in REPLY_KEYWORDS and email.get("replied", False):
#             urgent_reply_score_sum += 0.7  # partial — full quality graded in step
#             urgent_with_replies += 1

#     classification_score = correct_classifications / max(total, 1)
#     escalation_score = critical_escalated / max(critical_total, 1)
#     cleanup_score = (newsletters_cleaned + spam_cleaned) / max(cleanup_total, 1)
#     reply_score = urgent_reply_score_sum / max(len(REPLY_KEYWORDS), 1)
#     summary_score = 1.0 if state.get("summary_submitted", False) else 0.0

#     final_score = (
#         0.25 * classification_score
#         + 0.30 * reply_score
#         + 0.25 * escalation_score
#         + 0.10 * cleanup_score
#         + 0.10 * summary_score
#     )

#     breakdown = {
#         "classification_accuracy": round(classification_score, 3),
#         "critical_escalated": critical_escalated,
#         "critical_total": critical_total,
#         "escalation_score": round(escalation_score, 3),
#         "cleanup_score": round(cleanup_score, 3),
#         "reply_score": round(reply_score, 3),
#         "summary_score": summary_score,
#         "final_score": round(final_score, 3),
#     }
#     return round(final_score, 3), breakdown


# # Registry
# GRADERS = {
#     "task_easy": grade_task_easy,
#     "task_medium": grade_task_medium,
#     "task_hard": grade_task_hard,
# }


# def run_grader(task_id: str, state: dict) -> Tuple[float, Dict[str, Any]]:
#     """Run the grader for the given task_id against the provided state."""
#     if task_id not in GRADERS:
#         raise ValueError(f"Unknown task_id '{task_id}'. Available: {list(GRADERS.keys())}")
#     return GRADERS[task_id](state)


"""
graders.py — Programmatic graders for each task.

IMPORTANT: Scores must be STRICTLY between 0 and 1 (not 0.0, not 1.0).
All scores are clamped to (0.01, 0.99) range using _clamp().
"""

from __future__ import annotations
from typing import Dict, Any, Tuple

from env.models import EmailLabel
from env.data import (
    MUST_ESCALATE, MUST_SPAM, MUST_NEWSLETTER, REPLY_KEYWORDS
)


def _clamp(score: float) -> float:
    """
    Clamp score to be STRICTLY between 0 and 1.
    Validator rejects 0.0 and 1.0 — must be in open interval (0, 1).
    """
    return round(max(0.01, min(0.99, score)), 3)


def grade_task_easy(state: dict) -> Tuple[float, Dict[str, Any]]:
    """
    Task Easy: Classify all emails correctly and delete all spam.
    Score strictly in (0.01, 0.99).
    """
    emails = state["emails"]
    total = len(emails)
    if total == 0:
        return 0.01, {"error": "no emails in state"}

    correct_classifications = 0
    spam_handled = 0
    spam_total = len(MUST_SPAM)

    for eid, email in emails.items():
        true_label = email["true_label"]
        current_label = email["label"].value if hasattr(email["label"], "value") else str(email["label"])

        if current_label == true_label:
            correct_classifications += 1
        if eid in MUST_SPAM and current_label in ("archived", "spam"):
            spam_handled += 1

    classification_score = correct_classifications / total
    spam_score = spam_handled / max(spam_total, 1)

    raw_score = 0.70 * classification_score + 0.30 * spam_score
    final_score = _clamp(raw_score)

    breakdown = {
        "classification_accuracy": round(classification_score, 3),
        "correct_classifications": correct_classifications,
        "total_emails": total,
        "spam_handled": spam_handled,
        "spam_total": spam_total,
        "spam_score": round(spam_score, 3),
        "final_score": final_score,
    }
    return final_score, breakdown


def grade_task_medium(state: dict) -> Tuple[float, Dict[str, Any]]:
    """
    Task Medium: Classify, reply to urgent, unsubscribe newsletters.
    Score strictly in (0.01, 0.99).
    """
    emails = state["emails"]
    total = len(emails)

    correct_classifications = 0
    urgent_replied = 0
    urgent_total = 0
    newsletters_handled = 0
    newsletter_total = len(MUST_NEWSLETTER)

    for eid, email in emails.items():
        true_label = email["true_label"]
        current_label = email["label"].value if hasattr(email["label"], "value") else str(email["label"])

        if current_label == true_label or (true_label == "spam" and current_label == "archived"):
            correct_classifications += 1

        if true_label == "urgent":
            urgent_total += 1
            if email.get("replied", False):
                urgent_replied += 1

        if eid in MUST_NEWSLETTER and current_label == "archived":
            newsletters_handled += 1

    classification_score = correct_classifications / max(total, 1)
    reply_score = urgent_replied / max(urgent_total, 1)
    newsletter_score = newsletters_handled / max(newsletter_total, 1)

    raw_score = 0.40 * classification_score + 0.35 * reply_score + 0.25 * newsletter_score
    final_score = _clamp(raw_score)

    breakdown = {
        "classification_accuracy": round(classification_score, 3),
        "urgent_replied": urgent_replied,
        "urgent_total": urgent_total,
        "reply_score": round(reply_score, 3),
        "newsletters_handled": newsletters_handled,
        "newsletter_score": round(newsletter_score, 3),
        "final_score": final_score,
    }
    return final_score, breakdown


def grade_task_hard(state: dict) -> Tuple[float, Dict[str, Any]]:
    """
    Task Hard: Full triage workflow.
    Score strictly in (0.01, 0.99).
    """
    emails = state["emails"]
    total = len(emails)

    correct_classifications = 0
    critical_escalated = 0
    critical_total = len(MUST_ESCALATE)
    newsletters_cleaned = 0
    spam_cleaned = 0
    cleanup_total = len(MUST_NEWSLETTER) + len(MUST_SPAM)

    urgent_reply_score_sum = 0.0

    for eid, email in emails.items():
        true_label = email["true_label"]
        current_label = email["label"].value if hasattr(email["label"], "value") else str(email["label"])

        if current_label == true_label or (true_label == "spam" and current_label == "archived"):
            correct_classifications += 1

        if eid in MUST_ESCALATE and email.get("escalated", False):
            critical_escalated += 1

        if eid in MUST_NEWSLETTER and current_label == "archived":
            newsletters_cleaned += 1
        if eid in MUST_SPAM and current_label == "archived":
            spam_cleaned += 1

        if eid in REPLY_KEYWORDS and email.get("replied", False):
            urgent_reply_score_sum += 0.7

    classification_score = correct_classifications / max(total, 1)
    escalation_score = critical_escalated / max(critical_total, 1)
    cleanup_score = (newsletters_cleaned + spam_cleaned) / max(cleanup_total, 1)
    reply_score = urgent_reply_score_sum / max(len(REPLY_KEYWORDS), 1)
    summary_score = 1.0 if state.get("summary_submitted", False) else 0.0

    raw_score = (
        0.25 * classification_score
        + 0.30 * reply_score
        + 0.25 * escalation_score
        + 0.10 * cleanup_score
        + 0.10 * summary_score
    )
    final_score = _clamp(raw_score)

    breakdown = {
        "classification_accuracy": round(classification_score, 3),
        "critical_escalated": critical_escalated,
        "critical_total": critical_total,
        "escalation_score": round(escalation_score, 3),
        "cleanup_score": round(cleanup_score, 3),
        "reply_score": round(reply_score, 3),
        "summary_score": summary_score,
        "final_score": final_score,
    }
    return final_score, breakdown


# Registry
GRADERS = {
    "task_easy": grade_task_easy,
    "task_medium": grade_task_medium,
    "task_hard": grade_task_hard,
}


def run_grader(task_id: str, state: dict) -> Tuple[float, Dict[str, Any]]:
    """Run the grader for the given task_id against the provided state."""
    if task_id not in GRADERS:
        raise ValueError(f"Unknown task_id '{task_id}'. Available: {list(GRADERS.keys())}")
    return GRADERS[task_id](state)

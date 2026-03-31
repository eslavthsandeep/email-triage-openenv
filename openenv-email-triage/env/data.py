"""
data.py — Synthetic email dataset for the Email Triage environment.
Emails span multiple categories and difficulty levels.
"""

from typing import List, Dict

# Full email objects (id -> full body)
EMAIL_BODIES: Dict[str, str] = {
    "e001": (
        "Hi team,\n\n"
        "The production database is DOWN. We are seeing 500 errors across all endpoints. "
        "Customers are unable to log in. This started ~10 minutes ago. "
        "I've paged the on-call engineer but need manager sign-off to initiate the rollback procedure. "
        "PLEASE RESPOND IMMEDIATELY.\n\n"
        "— Priya (SRE)"
    ),
    "e002": (
        "Dear Valued Customer,\n\n"
        "You have WON a $1,000 Amazon Gift Card! Click the link below to claim your prize:\n"
        "http://totally-legit-prize.xyz/claim?id=abc123\n\n"
        "Hurry, offer expires in 24 hours!\n\n"
        "Best,\nPrize Team"
    ),
    "e003": (
        "Hey,\n\n"
        "Just a reminder that the Q2 planning meeting is scheduled for Thursday at 2 PM IST "
        "in Conference Room B. Agenda will be shared tomorrow.\n\n"
        "Thanks,\nRohan"
    ),
    "e004": (
        "Hi,\n\n"
        "This is your weekly digest from TechCrunch. Top stories this week:\n"
        "- OpenAI launches new model\n"
        "- Meta acquires VR startup\n"
        "- Indian startup ecosystem hits $10B funding in Q1\n\n"
        "Click here to read more or manage your subscription preferences.\n\n"
        "TechCrunch Newsletter Team"
    ),
    "e005": (
        "Hello,\n\n"
        "I'm writing regarding invoice #INV-2024-0892 which was due on March 15th. "
        "We have not received payment and the outstanding amount is ₹85,000. "
        "Please arrange payment within 48 hours to avoid a late fee. "
        "If there is a dispute, please contact us immediately.\n\n"
        "Regards,\nAccounts Receivable\nVendor Corp"
    ),
    "e006": (
        "Hi,\n\n"
        "Congratulations! You've been selected for an exclusive credit card offer. "
        "0% APR for 12 months. No annual fee. Apply now!\n"
        "Unsubscribe: http://spam-bank.com/unsub\n\n"
        "FinanceOffers Team"
    ),
    "e007": (
        "Hi,\n\n"
        "Could you please review the attached PR #342 when you get a chance? "
        "It's a refactor of the auth module. No rush — end of week is fine.\n\n"
        "Cheers,\nAmit"
    ),
    "e008": (
        "Team,\n\n"
        "SECURITY ALERT: We have detected an unauthorized login attempt on your account "
        "from IP 185.234.219.x (Russia). Your account has been temporarily locked. "
        "Please verify your identity within 2 hours or access will be permanently suspended. "
        "Contact security@company.com immediately.\n\n"
        "Security Team"
    ),
    "e009": (
        "Hi,\n\n"
        "Here's your monthly product newsletter:\n"
        "- New feature: Dark mode launched\n"
        "- Bug fix: Export to CSV now works on Safari\n"
        "- Upcoming: API v2 in April\n\n"
        "Thanks for using our product!\nProduct Team"
    ),
    "e010": (
        "Hello,\n\n"
        "I'm a senior engineer interviewing at your company next Monday. "
        "I wanted to confirm the interview schedule and ask if there's anything "
        "specific I should prepare. Looking forward to meeting the team!\n\n"
        "Best,\nSneha Patel"
    ),
}

# Email metadata for inbox listing
INBOX_EMAILS: List[Dict] = [
    {
        "id": "e001",
        "subject": "URGENT: Production DB is DOWN",
        "sender": "priya.sre@company.com",
        "timestamp": "2024-03-30T09:02:00",
        "snippet": "The production database is DOWN. We are seeing 500 errors across all endpoints...",
        "true_label": "urgent",
    },
    {
        "id": "e002",
        "subject": "Congratulations! You WON a $1,000 Gift Card",
        "sender": "noreply@totally-legit-prize.xyz",
        "timestamp": "2024-03-30T08:45:00",
        "snippet": "You have WON a $1,000 Amazon Gift Card! Click the link below to claim...",
        "true_label": "spam",
    },
    {
        "id": "e003",
        "subject": "Q2 Planning Meeting Reminder — Thursday 2PM",
        "sender": "rohan@company.com",
        "timestamp": "2024-03-30T08:30:00",
        "snippet": "Just a reminder that the Q2 planning meeting is scheduled for Thursday at 2 PM IST...",
        "true_label": "normal",
    },
    {
        "id": "e004",
        "subject": "TechCrunch Weekly Digest",
        "sender": "newsletter@techcrunch.com",
        "timestamp": "2024-03-30T07:00:00",
        "snippet": "This is your weekly digest from TechCrunch. Top stories this week: OpenAI launches...",
        "true_label": "newsletter",
    },
    {
        "id": "e005",
        "subject": "OVERDUE Invoice #INV-2024-0892 — Action Required",
        "sender": "ar@vendorcorp.com",
        "timestamp": "2024-03-29T17:00:00",
        "snippet": "Invoice #INV-2024-0892 was due on March 15th. Outstanding amount ₹85,000...",
        "true_label": "urgent",
    },
    {
        "id": "e006",
        "subject": "Exclusive Credit Card Offer — 0% APR",
        "sender": "offers@spam-bank.com",
        "timestamp": "2024-03-29T14:00:00",
        "snippet": "You've been selected for an exclusive credit card offer. 0% APR for 12 months...",
        "true_label": "spam",
    },
    {
        "id": "e007",
        "subject": "PR Review Request — Auth Module Refactor (#342)",
        "sender": "amit@company.com",
        "timestamp": "2024-03-29T11:00:00",
        "snippet": "Could you please review the attached PR #342 when you get a chance? It's a refactor...",
        "true_label": "normal",
    },
    {
        "id": "e008",
        "subject": "Security Alert: Unauthorized Login Attempt",
        "sender": "security@company.com",
        "timestamp": "2024-03-29T09:30:00",
        "snippet": "We have detected an unauthorized login attempt on your account from IP 185.234.219.x...",
        "true_label": "urgent",
    },
    {
        "id": "e009",
        "subject": "Monthly Product Newsletter — March 2024",
        "sender": "product@saas-tool.com",
        "timestamp": "2024-03-28T10:00:00",
        "snippet": "Here's your monthly product newsletter: New feature: Dark mode launched...",
        "true_label": "newsletter",
    },
    {
        "id": "e010",
        "subject": "Interview Confirmation — Monday",
        "sender": "sneha.patel@gmail.com",
        "timestamp": "2024-03-28T09:00:00",
        "snippet": "I'm a senior engineer interviewing at your company next Monday. Wanted to confirm...",
        "true_label": "normal",
    },
]

# Expected reply keywords for grading (email_id -> required concepts)
REPLY_KEYWORDS: Dict[str, List[str]] = {
    "e001": ["rollback", "escalat", "on-call", "acknowledg", "investigat"],
    "e005": ["payment", "invoice", "apologize", "process", "arrange"],
    "e008": ["security", "password", "verify", "investigat", "team"],
    "e010": ["confirm", "interview", "monday", "look forward", "prepar"],
}

# Emails that MUST be escalated in the hard task
MUST_ESCALATE = {"e001", "e008"}

# Emails that MUST be classified as spam
MUST_SPAM = {"e002", "e006"}

# Emails that MUST be classified as newsletter
MUST_NEWSLETTER = {"e004", "e009"}

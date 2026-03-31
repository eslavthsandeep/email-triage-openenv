"""
environment.py — Core Email Triage OpenEnv environment.

Implements the full OpenEnv interface:
  - reset() -> Observation
  - step(action: Action) -> (Observation, float, bool, dict)
  - state() -> dict

Reward function provides partial progress signals across the full trajectory.
"""

from __future__ import annotations
import copy
from typing import Dict, List, Optional, Tuple, Any

from env.models import (
    Action, ActionType, Observation, Reward,
    EmailMeta, EmailLabel, InboxStats
)
from env.data import (
    INBOX_EMAILS, EMAIL_BODIES, REPLY_KEYWORDS,
    MUST_ESCALATE, MUST_SPAM, MUST_NEWSLETTER
)


class EmailTriageEnv:
    """
    Real-world email triage environment for the OpenEnv hackathon.

    The agent must manage an inbox of 10 emails with varying urgency,
    performing classification, replies, escalations, and archiving.
    """

    MAX_STEPS = 50

    def __init__(self, task_id: str = "task_easy"):
        self.task_id = task_id
        self._emails: Dict[str, dict] = {}       # id -> mutable email state
        self._step_count = 0
        self._open_email_id: Optional[str] = None
        self._open_email_body: Optional[str] = None
        self._last_action_result = ""
        self._summary_submitted = False
        self._done = False
        self._initialize_emails()

    # ------------------------------------------------------------------
    # OpenEnv interface
    # ------------------------------------------------------------------

    def reset(self) -> Observation:
        """Reset the environment and return the initial observation."""
        self._emails = {}
        self._step_count = 0
        self._open_email_id = None
        self._open_email_body = None
        self._last_action_result = "Inbox loaded. You have 10 emails to triage."
        self._summary_submitted = False
        self._done = False
        self._initialize_emails()
        return self._build_observation()

    def step(self, action: Action) -> Tuple[Observation, float, bool, dict]:
        """
        Execute one action in the environment.

        Returns:
            observation: new Observation
            reward: float in [0, 1] — step reward (partial progress)
            done: bool
            info: dict with reward breakdown and debug info
        """
        if self._done:
            obs = self._build_observation()
            return obs, 0.0, True, {"error": "episode already done"}

        self._step_count += 1
        step_reward = 0.0
        info: Dict[str, Any] = {"step": self._step_count}

        # Dispatch action
        action_type = ActionType(action.action_type)

        if action_type == ActionType.READ:
            step_reward, msg = self._handle_read(action)
        elif action_type == ActionType.CLASSIFY:
            step_reward, msg = self._handle_classify(action)
        elif action_type == ActionType.REPLY:
            step_reward, msg = self._handle_reply(action)
        elif action_type == ActionType.DELETE:
            step_reward, msg = self._handle_delete(action)
        elif action_type == ActionType.ARCHIVE:
            step_reward, msg = self._handle_archive(action)
        elif action_type == ActionType.ESCALATE:
            step_reward, msg = self._handle_escalate(action)
        elif action_type == ActionType.UNSUBSCRIBE:
            step_reward, msg = self._handle_unsubscribe(action)
        elif action_type == ActionType.SUMMARIZE:
            step_reward, msg = self._handle_summarize(action)
        elif action_type == ActionType.NOOP:
            step_reward, msg = -0.01, "No action taken. A step was wasted."
        else:
            step_reward, msg = -0.02, f"Unknown action type: {action_type}"

        self._last_action_result = msg
        info["action_result"] = msg
        info["step_reward"] = step_reward

        # Check terminal conditions
        if self._step_count >= self.MAX_STEPS:
            self._done = True
            info["terminal_reason"] = "max_steps_reached"
        elif self._is_task_complete():
            self._done = True
            info["terminal_reason"] = "task_complete"
            # Bonus for completing before max steps
            step_reward += 0.05 * (1 - self._step_count / self.MAX_STEPS)

        obs = self._build_observation()
        return obs, float(min(max(step_reward, -0.1), 1.0)), self._done, info

    def state(self) -> dict:
        """Return full internal state as a dict (for debugging / evaluation)."""
        return {
            "task_id": self.task_id,
            "step": self._step_count,
            "done": self._done,
            "emails": copy.deepcopy(self._emails),
            "open_email_id": self._open_email_id,
            "summary_submitted": self._summary_submitted,
            "last_action_result": self._last_action_result,
        }

    # ------------------------------------------------------------------
    # Action handlers
    # ------------------------------------------------------------------

    def _handle_read(self, action: Action) -> Tuple[float, str]:
        eid = action.email_id
        if not eid or eid not in self._emails:
            return -0.01, f"Email ID '{eid}' not found."
        email = self._emails[eid]
        if email["label"] == EmailLabel.ARCHIVED:
            return 0.0, f"Email {eid} is archived. Retrieved body."
        reward = 0.02 if not email["read"] else 0.0
        email["read"] = True
        self._open_email_id = eid
        self._open_email_body = EMAIL_BODIES.get(eid, "[No body available]")
        return reward, f"Opened email '{email['subject']}'."

    def _handle_classify(self, action: Action) -> Tuple[float, str]:
        eid = action.email_id
        if not eid or eid not in self._emails:
            return -0.01, f"Email ID '{eid}' not found."
        label_str = (action.content or "").lower().strip()
        valid_labels = {l.value for l in EmailLabel} - {"unread", "archived", "escalated"}
        if label_str not in valid_labels:
            return -0.01, f"Invalid label '{label_str}'. Choose from: {', '.join(valid_labels)}."

        email = self._emails[eid]
        new_label = EmailLabel(label_str)
        true_label = email["true_label"]
        was_correct = (label_str == true_label)

        email["label"] = new_label
        reward = 0.08 if was_correct else -0.03
        feedback = "Correct!" if was_correct else f"Incorrect. This email is actually '{true_label}'."
        return reward, f"Classified '{email['subject']}' as '{label_str}'. {feedback}"

    def _handle_reply(self, action: Action) -> Tuple[float, str]:
        eid = action.email_id
        if not eid or eid not in self._emails:
            return -0.01, f"Email ID '{eid}' not found."
        email = self._emails[eid]
        if email.get("replied"):
            return 0.0, f"Already replied to '{email['subject']}'."

        body = (action.content or "").lower()
        keywords = REPLY_KEYWORDS.get(eid, [])
        if not keywords:
            # Replying to an email that doesn't need a reply (slight negative)
            return -0.02, f"Sent a reply to '{email['subject']}' but this email didn't require a response."

        matched = sum(1 for kw in keywords if kw in body)
        quality = matched / max(len(keywords), 1)
        email["replied"] = True

        if quality >= 0.6:
            reward = 0.15
            feedback = "High-quality reply — covered key points."
        elif quality >= 0.3:
            reward = 0.08
            feedback = "Partial reply — missed some important points."
        else:
            reward = 0.02
            feedback = "Low-quality reply — very few relevant points addressed."

        return reward, f"Replied to '{email['subject']}'. {feedback} (matched {matched}/{len(keywords)} keywords)"

    def _handle_delete(self, action: Action) -> Tuple[float, str]:
        eid = action.email_id
        if not eid or eid not in self._emails:
            return -0.01, f"Email ID '{eid}' not found."
        email = self._emails[eid]
        true_label = email["true_label"]
        if true_label == "spam":
            email["label"] = EmailLabel.ARCHIVED
            return 0.08, f"Deleted spam email '{email['subject']}'. Good catch!"
        else:
            return -0.05, f"Deleted '{email['subject']}' — but this was NOT spam! Penalised."

    def _handle_archive(self, action: Action) -> Tuple[float, str]:
        eid = action.email_id
        if not eid or eid not in self._emails:
            return -0.01, f"Email ID '{eid}' not found."
        email = self._emails[eid]
        if email["label"] == EmailLabel.ARCHIVED:
            return 0.0, f"Already archived."
        email["label"] = EmailLabel.ARCHIVED
        return 0.03, f"Archived '{email['subject']}'."

    def _handle_escalate(self, action: Action) -> Tuple[float, str]:
        eid = action.email_id
        if not eid or eid not in self._emails:
            return -0.01, f"Email ID '{eid}' not found."
        email = self._emails[eid]
        if email.get("escalated"):
            return 0.0, "Already escalated."
        email["escalated"] = True
        email["label"] = EmailLabel.ESCALATED
        if eid in MUST_ESCALATE:
            return 0.12, f"Correctly escalated critical email '{email['subject']}'."
        else:
            return -0.03, f"Escalated '{email['subject']}' — unnecessary escalation."

    def _handle_unsubscribe(self, action: Action) -> Tuple[float, str]:
        eid = action.email_id
        if not eid or eid not in self._emails:
            return -0.01, f"Email ID '{eid}' not found."
        email = self._emails[eid]
        true_label = email["true_label"]
        if true_label == "newsletter":
            email["unsubscribed"] = True
            email["label"] = EmailLabel.ARCHIVED
            return 0.06, f"Unsubscribed from newsletter '{email['subject']}'."
        else:
            return -0.02, f"Tried to unsubscribe from '{email['subject']}' — this is not a newsletter."

    def _handle_summarize(self, action: Action) -> Tuple[float, str]:
        if self.task_id != "task_hard":
            return 0.0, "Summary not required for this task."
        body = (action.content or "").lower()
        keywords = ["urgent", "spam", "archived", "newsletter", "reply", "escalat"]
        matched = sum(1 for kw in keywords if kw in body)
        quality = matched / len(keywords)
        self._summary_submitted = True
        reward = 0.10 * quality
        return reward, f"Summary submitted. Quality: {matched}/{len(keywords)} key concepts covered."

    # ------------------------------------------------------------------
    # Terminal check
    # ------------------------------------------------------------------

    def _is_task_complete(self) -> bool:
        if self.task_id == "task_easy":
            # All emails classified (not unread)
            return all(
                e["label"] != EmailLabel.UNREAD
                for e in self._emails.values()
            )
        elif self.task_id == "task_medium":
            # All classified + all urgent emails replied to
            all_classified = all(e["label"] != EmailLabel.UNREAD for e in self._emails.values())
            urgent_replied = all(
                e.get("replied", False)
                for e in self._emails.values()
                if e["true_label"] == "urgent"
            )
            return all_classified and urgent_replied
        elif self.task_id == "task_hard":
            all_classified = all(e["label"] != EmailLabel.UNREAD for e in self._emails.values())
            urgent_replied = all(
                e.get("replied", False)
                for e in self._emails.values()
                if e["true_label"] == "urgent" and e["id"] in REPLY_KEYWORDS
            )
            critical_escalated = all(
                e.get("escalated", False)
                for e in self._emails.values()
                if e["id"] in MUST_ESCALATE
            )
            return all_classified and urgent_replied and critical_escalated and self._summary_submitted
        return False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _initialize_emails(self):
        for raw in INBOX_EMAILS:
            self._emails[raw["id"]] = {
                **raw,
                "label": EmailLabel.UNREAD,
                "read": False,
                "replied": False,
                "escalated": False,
                "unsubscribed": False,
            }

    def _build_observation(self) -> Observation:
        email_metas = []
        for eid, e in self._emails.items():
            email_metas.append(EmailMeta(
                id=e["id"],
                subject=e["subject"],
                sender=e["sender"],
                timestamp=e["timestamp"],
                snippet=e["snippet"],
                label=e["label"],
                replied=e.get("replied", False),
                read=e.get("read", False),
            ))

        # Sort: unread first, then by timestamp desc
        email_metas.sort(key=lambda x: (x.label != EmailLabel.UNREAD, x.timestamp), reverse=False)

        stats = InboxStats(
            total=len(self._emails),
            unread=sum(1 for e in self._emails.values() if e["label"] == EmailLabel.UNREAD),
            urgent=sum(1 for e in self._emails.values() if e["label"] == EmailLabel.ESCALATED or e["true_label"] == "urgent"),
            spam=sum(1 for e in self._emails.values() if e["label"] in (EmailLabel.SPAM,)),
            archived=sum(1 for e in self._emails.values() if e["label"] == EmailLabel.ARCHIVED),
            escalated=sum(1 for e in self._emails.values() if e.get("escalated", False)),
        )

        return Observation(
            emails=email_metas,
            open_email_body=self._open_email_body,
            inbox_stats=stats,
            last_action_result=self._last_action_result,
            step=self._step_count,
            done=self._done,
            task_id=self.task_id,
        )

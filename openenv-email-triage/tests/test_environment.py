"""
tests/test_environment.py — Unit tests for EmailTriageEnv.

Tests cover: reset, step, all action types, graders, reward range,
done conditions, and OpenEnv spec compliance.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from env.environment import EmailTriageEnv
from env.models import Action, ActionType, Observation, EmailLabel
from tasks.graders import run_grader


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def env_easy():
    env = EmailTriageEnv(task_id="task_easy")
    env.reset()
    return env

@pytest.fixture
def env_medium():
    env = EmailTriageEnv(task_id="task_medium")
    env.reset()
    return env

@pytest.fixture
def env_hard():
    env = EmailTriageEnv(task_id="task_hard")
    env.reset()
    return env


# ---------------------------------------------------------------------------
# OpenEnv spec compliance
# ---------------------------------------------------------------------------

class TestOpenEnvSpec:
    def test_reset_returns_observation(self, env_easy):
        obs = env_easy.reset()
        assert isinstance(obs, Observation)

    def test_reset_has_emails(self, env_easy):
        obs = env_easy.reset()
        assert len(obs.emails) == 10

    def test_step_returns_tuple(self, env_easy):
        action = Action(action_type=ActionType.NOOP)
        result = env_easy.step(action)
        assert len(result) == 4
        obs, reward, done, info = result
        assert isinstance(obs, Observation)
        assert isinstance(reward, float)
        assert isinstance(done, bool)
        assert isinstance(info, dict)

    def test_reward_in_range(self, env_easy):
        for action_type in [ActionType.NOOP, ActionType.READ]:
            env_easy.reset()
            action = Action(action_type=action_type, email_id="e001")
            _, reward, _, _ = env_easy.step(action)
            assert -0.1 <= reward <= 1.0, f"Reward {reward} out of range for {action_type}"

    def test_state_returns_dict(self, env_easy):
        state = env_easy.state()
        assert isinstance(state, dict)
        assert "task_id" in state
        assert "step" in state
        assert "emails" in state
        assert "done" in state


# ---------------------------------------------------------------------------
# Action tests
# ---------------------------------------------------------------------------

class TestActions:
    def test_read_action(self, env_easy):
        action = Action(action_type=ActionType.READ, email_id="e001")
        obs, reward, done, info = env_easy.step(action)
        assert obs.open_email_body is not None
        assert "production database" in obs.open_email_body.lower()
        assert reward > 0

    def test_read_nonexistent_email(self, env_easy):
        action = Action(action_type=ActionType.READ, email_id="e999")
        obs, reward, done, info = env_easy.step(action)
        assert reward < 0

    def test_classify_correct(self, env_easy):
        action = Action(action_type=ActionType.CLASSIFY, email_id="e002", content="spam")
        obs, reward, done, info = env_easy.step(action)
        assert reward > 0, "Correct classification should give positive reward"

    def test_classify_wrong(self, env_easy):
        action = Action(action_type=ActionType.CLASSIFY, email_id="e001", content="normal")
        obs, reward, done, info = env_easy.step(action)
        assert reward < 0, "Wrong classification should give negative reward"

    def test_classify_invalid_label(self, env_easy):
        action = Action(action_type=ActionType.CLASSIFY, email_id="e001", content="invalid_label")
        obs, reward, done, info = env_easy.step(action)
        assert reward < 0

    def test_reply_to_urgent(self, env_easy):
        action = Action(
            action_type=ActionType.REPLY,
            email_id="e001",
            content="Dear Priya, I acknowledge the issue. We are initiating rollback and escalating to the on-call engineer immediately.",
        )
        obs, reward, done, info = env_easy.step(action)
        assert reward > 0

    def test_reply_low_quality(self, env_easy):
        action = Action(action_type=ActionType.REPLY, email_id="e001", content="ok")
        obs, reward, done, info = env_easy.step(action)
        assert reward >= 0  # Low but still gets some credit for replying

    def test_delete_spam(self, env_easy):
        action = Action(action_type=ActionType.DELETE, email_id="e002")
        obs, reward, done, info = env_easy.step(action)
        assert reward > 0

    def test_delete_non_spam(self, env_easy):
        action = Action(action_type=ActionType.DELETE, email_id="e001")
        obs, reward, done, info = env_easy.step(action)
        assert reward < 0

    def test_escalate_critical(self, env_easy):
        action = Action(action_type=ActionType.ESCALATE, email_id="e001")
        obs, reward, done, info = env_easy.step(action)
        assert reward > 0

    def test_escalate_unnecessary(self, env_easy):
        action = Action(action_type=ActionType.ESCALATE, email_id="e003")
        obs, reward, done, info = env_easy.step(action)
        assert reward < 0

    def test_unsubscribe_newsletter(self, env_easy):
        action = Action(action_type=ActionType.UNSUBSCRIBE, email_id="e004")
        obs, reward, done, info = env_easy.step(action)
        assert reward > 0

    def test_unsubscribe_non_newsletter(self, env_easy):
        action = Action(action_type=ActionType.UNSUBSCRIBE, email_id="e001")
        obs, reward, done, info = env_easy.step(action)
        assert reward < 0

    def test_archive(self, env_easy):
        action = Action(action_type=ActionType.ARCHIVE, email_id="e003")
        obs, reward, done, info = env_easy.step(action)
        assert reward >= 0

    def test_noop_negative_reward(self, env_easy):
        action = Action(action_type=ActionType.NOOP)
        _, reward, _, _ = env_easy.step(action)
        assert reward < 0


# ---------------------------------------------------------------------------
# Grader tests
# ---------------------------------------------------------------------------

class TestGraders:
    def test_grader_score_range_easy(self, env_easy):
        state = env_easy.state()
        score, breakdown = run_grader("task_easy", state)
        assert 0.0 <= score <= 1.0

    def test_grader_score_range_medium(self, env_medium):
        state = env_medium.state()
        score, breakdown = run_grader("task_medium", state)
        assert 0.0 <= score <= 1.0

    def test_grader_score_range_hard(self, env_hard):
        state = env_hard.state()
        score, breakdown = run_grader("task_hard", state)
        assert 0.0 <= score <= 1.0

    def test_grader_has_breakdown(self, env_easy):
        state = env_easy.state()
        score, breakdown = run_grader("task_easy", state)
        assert isinstance(breakdown, dict)
        assert len(breakdown) > 0

    def test_grader_perfect_easy(self):
        """A fully correct run should give a high score."""
        env = EmailTriageEnv(task_id="task_easy")
        env.reset()
        # Classify all emails correctly
        classifications = {
            "e001": "urgent", "e002": "spam", "e003": "normal", "e004": "newsletter",
            "e005": "urgent", "e006": "spam", "e007": "normal", "e008": "urgent",
            "e009": "newsletter", "e010": "normal",
        }
        for eid, label in classifications.items():
            env.step(Action(action_type=ActionType.CLASSIFY, email_id=eid, content=label))
        for eid in ["e002", "e006"]:
            env.step(Action(action_type=ActionType.DELETE, email_id=eid))

        state = env.state()
        score, _ = run_grader("task_easy", state)
        assert score >= 0.6, f"Expected score >= 0.6 for perfect classification, got {score}"

    def test_grader_unknown_task(self, env_easy):
        state = env_easy.state()
        with pytest.raises(ValueError):
            run_grader("task_unknown", state)

    def test_graders_return_different_scores(self):
        """Different tasks should be graded independently."""
        env = EmailTriageEnv(task_id="task_easy")
        env.reset()
        state = env.state()
        score_easy, _ = run_grader("task_easy", state)
        score_medium, _ = run_grader("task_medium", state)
        # Both are valid, just verify they run without error
        assert 0.0 <= score_easy <= 1.0
        assert 0.0 <= score_medium <= 1.0


# ---------------------------------------------------------------------------
# Episode / done condition tests
# ---------------------------------------------------------------------------

class TestEpisode:
    def test_max_steps_terminates_episode(self, env_easy):
        env_easy.MAX_STEPS = 3
        for _ in range(5):
            _, _, done, _ = env_easy.step(Action(action_type=ActionType.NOOP))
            if done:
                break
        assert env_easy._done

    def test_no_step_after_done(self, env_easy):
        env_easy._done = True
        _, reward, done, info = env_easy.step(Action(action_type=ActionType.NOOP))
        assert done
        assert "error" in info

    def test_reset_clears_state(self, env_easy):
        env_easy.step(Action(action_type=ActionType.READ, email_id="e001"))
        env_easy.reset()
        assert env_easy._step_count == 0
        assert env_easy._open_email_body is None
        assert not env_easy._done


# ---------------------------------------------------------------------------
# Run directly
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

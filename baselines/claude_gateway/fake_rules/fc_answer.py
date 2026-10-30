"""The benchmark's FactConsolidation answer prompt (every method's final answering call)."""

from baselines.claude_gateway.fake import FakeReply, FakeRequest

PRIORITY = 90  # after the system-specific rules, which may embed this prompt inside their own

FAKE_ANSWER = "FAKE ANSWER"


def rule(request: FakeRequest) -> FakeReply | None:
    if "knowledge management system" in request.last_user_text and not request.tools:
        return FakeReply(FAKE_ANSWER)
    return None

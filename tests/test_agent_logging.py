from ai import agent_logging, router
from ai.agents.memory_operation import SavedMemoryResult, SearchMemoryResult


class FakeBoundLogger:
    def __init__(self):
        self.bound = None
        self.events = []

    def bind(self, **kwargs):
        self.bound = kwargs
        return self

    def info(self, event, **kwargs):
        self.events.append((event, kwargs))


def test_get_agent_logger_binds_agent_name(monkeypatch):
    fake_logger = FakeBoundLogger()
    monkeypatch.setattr(agent_logging.structlog, "get_logger", lambda: fake_logger)

    logger = agent_logging.get_agent_logger("router")

    assert logger is fake_logger
    assert fake_logger.bound == {"agent_name": "router"}


def test_snapshot_context_truncates_and_limits():
    long_text = "x" * (agent_logging.MAX_CONTEXT_STRING_LENGTH + 25)

    context = agent_logging.snapshot_context(
        long_text=long_text,
        items=list(range(agent_logging.MAX_CONTEXT_COLLECTION_ITEMS + 2)),
        nested={"a": {"b": {"c": {"d": "value"}}}},
    )

    assert context["long_text"].endswith("chars>")
    assert context["items"][-1] == "<truncated>"
    assert context["nested"]["a"]["b"]["c"]["d"] == "<max-depth>"


def test_route_message_logs_agent_context(monkeypatch):
    events = []

    class FakeLogger:
        def info(self, event, **kwargs):
            events.append((event, kwargs))

    class FakeStructuredLLM:
        def invoke(self, _messages):
            return router.RouterDecision(intent="search_memory", reasoning="retrieval question")

    class FakeChatOpenAI:
        def __init__(self, *args, **kwargs):
            self.kwargs = kwargs

        def with_structured_output(self, _schema):
            return FakeStructuredLLM()

    monkeypatch.setattr(router, "log", FakeLogger())
    monkeypatch.setattr(router, "ChatOpenAI", FakeChatOpenAI)
    monkeypatch.setattr(
        router,
        "search_memory",
        lambda user_id, message: SearchMemoryResult(query=message, memories=[]),
    )
    monkeypatch.setattr(
        router,
        "chat",
        lambda message, operation_result, recent_history=None: "reply",
    )

    result = router.route_message(
        user_id=1,
        message="What did I say about Lisbon?",
        recent_history="User asked about trips.",
    )

    assert result == "reply"
    assert events[0][0] == "agent_invoked"
    assert events[0][1]["model"] == router.ROUTER_MODEL
    assert events[0][1]["agent_context"]["message"] == "What did I say about Lisbon?"
    assert events[0][1]["agent_context"]["recent_history"] == "User asked about trips."
    assert events[1] == (
        "router_decision",
        {"intent": "search_memory", "reasoning": "retrieval question"},
    )


def test_route_message_uses_save_memory_before_chat(monkeypatch):
    class FakeStructuredLLM:
        def invoke(self, _messages):
            return router.RouterDecision(intent="save_memory", reasoning="new information to store")

    class FakeChatOpenAI:
        def __init__(self, *args, **kwargs):
            self.kwargs = kwargs

        def with_structured_output(self, _schema):
            return FakeStructuredLLM()

    captured = {}

    monkeypatch.setattr(router, "ChatOpenAI", FakeChatOpenAI)
    monkeypatch.setattr(
        router,
        "save_memory",
        lambda user_id, message, recent_history=None: SavedMemoryResult(
            saved_content="Favorite coffee is cortado",
            keywords=["coffee", "cortado", "preference"],
        ),
    )

    def fake_chat(message, operation_result, recent_history=None):
        captured["message"] = message
        captured["operation"] = operation_result
        captured["recent_history"] = recent_history
        return "final reply"

    monkeypatch.setattr(router, "chat", fake_chat)

    result = router.route_message(
        user_id=1,
        message="My favorite coffee is cortado",
        recent_history="Assistant asked about coffee.",
    )

    assert result == "final reply"
    assert captured["message"] == "My favorite coffee is cortado"
    assert captured["operation"].operation == "save_memory"
    assert captured["operation"].saved_content == "Favorite coffee is cortado"
    assert captured["recent_history"] == "Assistant asked about coffee."

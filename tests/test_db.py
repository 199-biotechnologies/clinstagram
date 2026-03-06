from clinstagram.db import Database


def test_init_creates_tables(tmp_path):
    db = Database(tmp_path / "test.db")
    tables = db.list_tables()
    assert "rate_limits" in tables
    assert "capabilities" in tables
    assert "audit_log" in tables
    assert "user_cache" in tables
    assert "thread_map" in tables


def test_record_rate_limit(tmp_path):
    db = Database(tmp_path / "test.db")
    db.record_action("default", "graph_fb", "dm_send")
    db.record_action("default", "graph_fb", "dm_send")
    count = db.get_action_count("default", "graph_fb", "dm_send", window_minutes=60)
    assert count == 2


def test_check_rate_limit_within_budget(tmp_path):
    db = Database(tmp_path / "test.db")
    assert db.check_rate_limit("default", "graph_fb", "dm_send", limit=200, window_minutes=60)


def test_check_rate_limit_exceeded(tmp_path):
    db = Database(tmp_path / "test.db")
    for _ in range(5):
        db.record_action("default", "private", "dm_send")
    assert not db.check_rate_limit("default", "private", "dm_send", limit=5, window_minutes=60)


def test_cache_user(tmp_path):
    db = Database(tmp_path / "test.db")
    db.cache_user("alice", user_id="123", private_pk="456")
    user = db.get_cached_user("alice")
    assert user["user_id"] == "123"
    assert user["private_pk"] == "456"


def test_cache_user_miss(tmp_path):
    db = Database(tmp_path / "test.db")
    assert db.get_cached_user("nonexistent") is None


def test_audit_log(tmp_path):
    db = Database(tmp_path / "test.db")
    db.log_audit("default", "graph_fb", "dm send", '{"user": "@alice"}', 0, "sent")
    rows = db.get_recent_audit(limit=1)
    assert len(rows) == 1
    assert rows[0]["command"] == "dm send"

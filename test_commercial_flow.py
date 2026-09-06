"""Commercial layer smoke test: account -> research history -> watchlist persistence."""
import os
import tempfile


def main():
    with tempfile.TemporaryDirectory() as td:
        os.environ["VALUESTOCK_DB_PATH"] = os.path.join(td, "test.db")

        # Import after setting DB path so the test never touches production data.
        from user_store import (
            add_watchlist_stock,
            get_watchlist,
            latest_research_for_codes,
            remove_watchlist_stock,
            save_research_snapshot,
            upsert_user,
        )

        user = upsert_user("smoke@example.com", "Smoke Test")
        uid = user["user_id"]

        save_research_snapshot(
            uid,
            {
                "code": "000333",
                "name": "美的集团",
                "score": 82,
                "decision": "🟢 可以分批建仓",
                "price": 70,
                "normal_value": 85,
                "safety_margin": 21.43,
            },
        )
        latest = latest_research_for_codes(uid, ["000333"])
        assert latest["000333"]["name"] == "美的集团"
        assert float(latest["000333"]["score"]) == 82

        assert add_watchlist_stock(uid, "000333", 20)
        assert add_watchlist_stock(uid, "601899", 20)
        assert get_watchlist(uid) == ["601899", "000333"]

        remove_watchlist_stock(uid, "601899")
        assert get_watchlist(uid) == ["000333"]

    print("commercial flow smoke test: PASS")


if __name__ == "__main__":
    main()

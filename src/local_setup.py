from src.db import get_session, init_db
from src.db_models import User
from src.enums import PlayerTurnState
from src.utils.jwt import hash_password


def create_test_user(db, id: int):
    password = "pass"
    hashed = hash_password(password)
    db.add(
        User(
            nickname=f"user_{id}",
            password_hash=hashed,
            first_name=f"User_{id}",
            url_handle=f"user{id}",
            is_online=0,
            current_game=None,
            current_game_updated_at=None,
            online_count=0,
            current_auc_total_sum=None,
            current_auc_started_at=None,
            pointauc_token=None,
            twitch_stream_link=None,
            vk_stream_link=None,
            kick_stream_link=None,
            telegram_link=None,
            donation_link=None,
            is_active=1,
            sector_id=1,
            total_score=0.0,
            turn_state=PlayerTurnState.INITIAL.value,
            last_dice_roll_id=None,
            maps_completed=0,
        )
    )


if __name__ == "__main__":
    init_db()

    print("Database initialized successfully.")

    with get_session() as db:
        users_count = db.query(User).count()
        if users_count == 0:
            [create_test_user(db, i + 1) for i in range(8)]
            db.commit()
            print("Test users created successfully.")

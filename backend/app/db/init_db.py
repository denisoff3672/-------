from app.db.seed import seed_default_tariffs, seed_predefined_users
from app.db.session import SessionLocal


def run_seed() -> None:
    db = SessionLocal()
    try:
        seed_default_tariffs(db)
        seed_predefined_users(db)
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()

from app.db.seed import seed_default_tariffs
from app.db.session import SessionLocal


def run_seed() -> None:
    db = SessionLocal()
    try:
        seed_default_tariffs(db)
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()

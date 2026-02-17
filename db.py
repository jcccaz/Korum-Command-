from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


def init_db(app) -> None:
    """Initialize SQLAlchemy and create tables without migrations."""
    db.init_app(app)
    with app.app_context():
        db.create_all()

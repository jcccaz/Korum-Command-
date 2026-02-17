from db import db
from datetime import datetime
import uuid
from werkzeug.security import check_password_hash, generate_password_hash


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    hashed_password = db.Column(db.String(255), nullable=False)

    def set_password(self, raw_password: str) -> None:
        self.hashed_password = generate_password_hash(raw_password)

    def verify_password(self, raw_password: str) -> bool:
        return check_password_hash(self.hashed_password, raw_password)

    def __repr__(self) -> str:
        return f"<User {self.email}>"


class UsageLog(db.Model):
    __tablename__ = "usage_logs"

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(
        db.String(36), default=lambda: str(uuid.uuid4()), index=True
    )
    user_id = db.Column(db.Integer, nullable=True)
    model = db.Column(db.String(50), nullable=False)
    persona = db.Column(db.String(100), nullable=True)
    tokens_input = db.Column(db.Integer, nullable=True)
    tokens_output = db.Column(db.Integer, nullable=True)
    cost_estimate = db.Column(db.Float, nullable=True)
    latency_ms = db.Column(db.Integer, nullable=True)
    success = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

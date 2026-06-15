import json
from http import HTTPStatus
from typing import Dict, Optional

from flask import Flask, request, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import Session

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///db.sqlite"
db = SQLAlchemy(app)

class Post(db.Model):
    id: int
    title: str
    body: str

    def __init__(self, title: str, body: str):
        self.title = title
        self.body = body

    @staticmethod
    def from_json(data: Dict[str, str]) -> "Post":
        return Post(data["title"], data["body"])

class Notification(db.Model):
    id: int
    user_id: int
    notification_id: int
    status: str

    def __init__(self, user_id: int, notification_id: int, status: str = "unread"):
        self.user_id = user_id
        self.notification_id = notification_id
        self.status = status

    @staticmethod
    def from_json(data: Dict[str, str]) -> "Notification":
        return Notification(int(data["user_id"]), int(data["notification_id"]))

@app.route("/api/submit", methods=["POST"])
def submit() -> Optional[Dict[str, str]]:
    data = request.get_json()
    if not data or "title" not in data or "body" not in data:
        return {"error": "Missing title or body"}, HTTPStatus.BAD_REQUEST
    post = Post.from_json(data)
    db.session.add(post)
    db.session.commit()
    return {"id": str(post.id)}, HTTPStatus.CREATED

@app.route("/api/notification/mark-read", methods=["POST"])
def mark_read() -> Optional[Dict[str, str]]:
    data = request.get_json()
    if not data or "notification_id" not in data:
        return {"error": "Missing notification ID"}, HTTPStatus.BAD_REQUEST
    notification_id = int(data["notification_id"])
    user_id = session.get("user_id")
    if not user_id:
        return {"error": "User not authenticated"}, HTTPStatus.UNAUTHORIZED
    notification = Notification.query.filter_by(user_id=user_id, id=notification_id).first()
    if not notification:
        return {"error": "Notification not found"}, HTTPStatus.NOT_FOUND
    notification.status = "read"
    db.session.commit()
    return {}, HTTPStatus.OK
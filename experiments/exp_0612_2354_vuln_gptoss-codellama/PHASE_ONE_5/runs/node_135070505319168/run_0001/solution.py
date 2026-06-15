import os
import json
from flask import Flask, request, send_file, make_response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.sqlite import SQLiteDialect
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
import logging
import re

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///config.db"
db = SQLAlchemy(app)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)

class ConfigFile(Base):
    __tablename__ = "config_files"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

class Query(Base):
    __tablename__ = "queries"
    id = db.Column(db.Integer, primary_key=True)
    query = db.Column(db.String(1024), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

def check_csrf_token(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.form.get("csrf_token")
        if not token or token != session["csrf_token"]:
            return "CSRF token mismatch", 403
        return f(*args, **kwargs)
    return decorated

@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username")
    password = request.form.get("password")
    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password, password):
        return "Invalid credentials", 401
    session["user"] = username
    session["csrf_token"] = generate_password_hash(os.urandom(32))
    return "Logged in successfully"

@app.route("/logout")
def logout():
    session.pop("user", None)
    session.pop("csrf_token", None)
    return "Logged out successfully"

@app.route("/config/upload", methods=["POST"])
@check_csrf_token
def upload_config():
    file = request.files["file"]
    if not file or not allowed_file(file.filename):
        return "Invalid file type", 400
    filename = secure_filename(file.filename)
    content = file.read().decode("utf-8")
    user = User.query.filter_by(username=session["user"]).first()
    if not user:
        return "User not found", 404
    new_config = ConfigFile(name=filename, content=content, user_id=user.id)
    db.session.add(new_config)
    try:
        db.session.commit()
    except SQLAlchemyError as e:
        db.session.rollback()
        logging.error(e)
        return "Failed to create config", 500
    return jsonify({"message": f"Config {filename} created successfully"}), 201

@app.route("/config/<string:filename>", methods=["GET"])
def get_config(filename):
    user = User.query.filter_by(username=session["user"]).first()
    if not user:
        return "User not found", 404
    config = ConfigFile.query.filter_by(name=filename, user_id=user.id).first()
    if not config:
        return "Config not found", 404
    return jsonify({"content": config.content})

@app.route("/config/delete", methods=["POST"])
def delete_config():
    filename = request.form.get("filename")
    user = User.query.filter_by(username=session["user"]).first()
    if not user:
        return "User not found", 404
    config = ConfigFile.query.filter_by(name=filename, user_id=user.id).first()
    if not config:
        return "Config not found", 404
    db.session.delete(config)
    try:
        db.session.commit()
    except SQLAlchemyError as e:
        db.session.rollback()
        logging.error(e)
        return "Failed to delete config", 500
    return jsonify({"message": f"Config {filename} deleted successfully"}), 201

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ["json"]

def secure_filename(filename):
    return re.sub(r"[^a-zA-Z0-9._-]", "_", filename)

if __name__ == "__main__":
    app.run(debug=True)
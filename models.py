from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint, UniqueConstraint, Index

db = SQLAlchemy()
EVERYONE_ID = 0  # 0 + is_group=False = shared with everyone


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True, nullable=False)


class Group(db.Model):
    __tablename__ = "groups"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True, nullable=False)


class UserGroup(db.Model):
    __tablename__ = "user_groups"
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("groups.id"), primary_key=True)
    __table_args__ = (
        Index("ix_user_groups_user", "user_id"),
        Index("ix_user_groups_group", "group_id"),
    )


class Resource(db.Model):
    __tablename__ = "resources"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True, nullable=False)


class ResourceSharing(db.Model):
    """
    is_group=False, subject_id>0  -> shared with that user
    is_group=True,  subject_id>0  -> shared with that group
    is_group=False, subject_id=0  -> shared with everyone (global)
    """
    __tablename__ = "resource_sharing"
    id = db.Column(db.Integer, primary_key=True)
    resource_id = db.Column(db.Integer, db.ForeignKey("resources.id"), nullable=False)
    subject_id = db.Column(db.Integer, nullable=False, default=EVERYONE_ID)
    is_group = db.Column(db.Boolean, nullable=False, default=False)

    __table_args__ = (
        CheckConstraint("subject_id >= 0", name="ck_subject_id_nonneg"),
        UniqueConstraint("resource_id", "subject_id", "is_group",
                         name="uq_resource_sharing_unique"),
        Index("ix_sharing_resource_type", "resource_id", "is_group", "subject_id"),
        Index("ix_sharing_user_resource", "subject_id", "resource_id"),
        Index("ix_sharing_group_resource", "is_group", "subject_id", "resource_id"),
    )

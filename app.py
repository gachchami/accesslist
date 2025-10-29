import traceback
from flask import Flask, jsonify, abort
from sqlalchemy import select, union_all, func, distinct, exists, case, literal
from models import db, User, UserGroup, Resource, ResourceSharing, EVERYONE_ID
from werkzeug.exceptions import HTTPException

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///acl.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = True

db.init_app(app)

@app.errorhandler(HTTPException)
def handle_http_exception(e: HTTPException):
    traceback.print_exc()
    payload = {
        "error": {
            "type": e.__class__.__name__,
            "code": e.code,
            "message": e.description,
        }
    }
    return jsonify(payload), e.code

@app.errorhandler(Exception)
def handle_exception(e: Exception):
    traceback.print_exc()
    payload = {
        "error": {
            "type": "InternalServerError",
            "code": 500,
            "message": "Internal Server Error",
        }
    }
    return jsonify(payload), 500

def pairs_cte():
    """
    Returns a CTE 'pairs(resource_id, user_id)' of DISTINCT (resource, user)
    edges representing access via:
      - direct shares,
      - group shares,
      - global shares (everyone -> all users).
    """
    direct = select(
        ResourceSharing.resource_id,
        ResourceSharing.subject_id.label("user_id"),
    ).where(
        ResourceSharing.is_group.is_(False),
        ResourceSharing.subject_id > 0,
    )

    via_group = select(
        ResourceSharing.resource_id,
        UserGroup.user_id,
    ).join(
        UserGroup, ResourceSharing.subject_id == UserGroup.group_id
    ).where(
        ResourceSharing.is_group.is_(True),
    )

    global_users = select(
        ResourceSharing.resource_id,
        User.id.label("user_id"),
    ).select_from(ResourceSharing).join(
        User, literal(True)  # CROSS JOIN via ON TRUE
    ).where(
        ResourceSharing.is_group.is_(False),
        ResourceSharing.subject_id == EVERYONE_ID,
    )

    unioned = union_all(direct, via_group, global_users).cte("unioned")
    pairs = select(
        distinct(unioned.c.resource_id).label("resource_id"),
        unioned.c.user_id.label("user_id"),
    ).cte("pairs")

    return pairs


def global_share_exists(resource_id: str):
    return select(
        exists().where(
            ResourceSharing.resource_id == resource_id,
            ResourceSharing.is_group.is_(False),
            ResourceSharing.subject_id == EVERYONE_ID,
        )
    )    


@app.get("/resource/<int:resource_id>/access-list")
def resource_access_list(resource_id: int):
    resource = db.session.get(Resource, resource_id)
    if resource is None:
        abort(404, description=f"resource_not_found: {resource_id}")
    
    global_exists = db.session.execute(global_share_exists(resource_id)).scalar()
    if global_exists: 
        rows = db.session.execute(
            select(User.id, User.name).order_by(User.id)
            ).mappings().all()
        return jsonify([dict(r) for r in rows])

    direct_q = select(distinct(ResourceSharing.subject_id).label("user_id")).where(
        ResourceSharing.resource_id == resource_id,
        ResourceSharing.is_group.is_(False),
        ResourceSharing.subject_id > 0,
    )

    via_group_q = select(distinct(UserGroup.user_id).label("user_id")).join(
        ResourceSharing, ResourceSharing.subject_id == UserGroup.group_id
    ).where(
        ResourceSharing.resource_id == resource_id,
        ResourceSharing.is_group.is_(True),
    )

    combined = direct_q.union(via_group_q)
    sub = combined.subquery()
    rows = db.session.execute(
        select(User.id, User.name)
        .where(User.id.in_(select(sub.c.user_id)))
        .order_by(User.id)
    ).mappings().all()

    return jsonify([dict(r) for r in rows])

@app.get("/user/<int:user_id>/resources")
def user_resource_list(user_id: int):
    user = db.session.get(User, user_id)
    if user is None:
        abort(404, description=f"user_not_found: {user_id}")

    group_ids = [gid for (gid,) in db.session.execute(
        select(UserGroup.group_id).where(UserGroup.user_id == user_id)
    ).all()]
    subject_ids = [EVERYONE_ID, user_id]

    resource_ids_userq = select(
        distinct(ResourceSharing.resource_id).label("resource_id")).where(
            ResourceSharing.subject_id.in_(subject_ids),
                    ResourceSharing.is_group.is_(False),
            )
    resource_ids_groupq = select(
        distinct(ResourceSharing.resource_id).label("resource_id")).where(
            ResourceSharing.subject_id.in_(group_ids),
                    ResourceSharing.is_group.is_(True),
            )
    resource_ids_subq = resource_ids_userq.union(resource_ids_groupq)
    rows = db.session.execute(
        select(Resource.id, Resource.name)
        .where(Resource.id.in_(select(resource_ids_subq.c.resource_id)))
        .order_by(Resource.id)
    ).mappings().all()

    return jsonify([dict(r) for r in rows])

@app.get("/resources/with-user-count")
def resources_with_user_count():
    total_users_sq = select(func.count(User.id)).scalar_subquery()

    global_exists = exists(
        select(literal(1)).where(
            ResourceSharing.resource_id == Resource.id,
            ResourceSharing.is_group.is_(False),
            ResourceSharing.subject_id == EVERYONE_ID,   
        )
    )

    direct = select(
        ResourceSharing.resource_id,
        ResourceSharing.subject_id.label("user_id"),
    ).where(
        ResourceSharing.is_group.is_(False),
        ResourceSharing.subject_id > 0,   
    )

    via_group = select(
        ResourceSharing.resource_id,
        UserGroup.user_id,
    ).join(
        ResourceSharing, ResourceSharing.subject_id == UserGroup.group_id
    ).where(
        ResourceSharing.is_group.is_(True),
    )

    pairs = union_all(direct, via_group).subquery("pairs")

    q = (
        select(
            Resource.id.label("resource_id"),
            Resource.name.label("resource"),
            case(
                (global_exists, total_users_sq),
                else_=func.count(func.distinct(pairs.c.user_id)),
            ).label("user_count"),
        )
        .select_from(Resource)
        .outerjoin(pairs, pairs.c.resource_id == Resource.id)
        .group_by(Resource.id, Resource.name)
        .order_by(Resource.id)
    )

    rows = db.session.execute(q).mappings().all()
    return jsonify([dict(r) for r in rows])


@app.get("/users/with-resource-count")
def users_with_resource_count():
    pairs = pairs_cte()
    q = (
        select(
            User.id.label("user_id"),
            User.name.label("user"),
            func.count(pairs.c.resource_id).label("resource_count"),
        )
        .select_from(User)
        .outerjoin(pairs, pairs.c.user_id == User.id)
        .group_by(User.id, User.name)
        .order_by(User.id)
    )
    rows = db.session.execute(q).mappings().all()
    return jsonify([dict(r) for r in rows])

if __name__ == "__main__":
    app.run(debug=True)


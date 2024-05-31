from flask import Blueprint, request, jsonify
from marshmallow import ValidationError
from extensions import db, pwd_context, jwt
from website.schemas.user_schema import UserCreateSchema, UserSchema

auth_blueprint = Blueprint("auth", __name__, url_prefix="/auth")


# register a new user
@auth_blueprint.route("/register", methods=["POST"])
def register():
    if not request.is_json:
        return {"message": "Missing JSON in request"}, 400


    if request.method == "POST":
        schema = UserCreateSchema()
        user = schema.load(request.json)
        db.session.add(user)
        db.session.commit()


        schema = UserSchema()

    return {"message": "Registered successfully", "user": schema.dump(user)}, 201


@auth_blueprint.errorhandler(ValidationError)
def validation_error(e):
    return jsonify(e.messages), 400

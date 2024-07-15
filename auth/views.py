from flask import Blueprint, request, jsonify, render_template
from flask import current_app as cur_app
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, \
    get_jwt_identity, get_jwt
from marshmallow import ValidationError

from auth.token_helper import add_token_to_db, revoke_token_from_db, is_token_revoked
from extensions import db, pwd_context, jwt
from website.forms import UserForm
from website.models.users import User
from website.schemas.user_schema import UserCreateSchema, UserSchema

auth_blueprint = Blueprint("auth", __name__, url_prefix="/auth")

# return render_template('add_record.html', form=form, name=name)

# # register a new user
# @auth_blueprint.route("/register", methods=["POST", "GET"])
# def register():
#     if not request.is_json:
#         return {"message": "Missing JSON in request"}, 400
#
#
#     if request.method == "POST":
#         schema = UserCreateSchema()
#         user = schema.load(request.json)
#         db.session.add(user)
#         db.session.commit()
#
#
#         schema = UserSchema()
#
#     return {"message": "Registered successfully", "user": schema.dump(user)}, 201
@auth_blueprint.route("/register", methods=["POST", "GET"])
def register():
    form = UserForm()
    if form.validate_on_submit():
        schema = UserSchema()
        register_user = UserSchema().load(form.data)
        db.session.add(register_user)
        db.session.commit()
        schema = UserSchema()
    return render_template('register.html', form=form)




@auth_blueprint.route("/login", methods=["POST"])
def login():
    if not request.is_json:
        return {"message": "Missing JSON in request"}, 400

    email = request.json.get("email")
    password = request.json.get("password")

    if not email or not password:
        return {"message": "Missing email or password"}, 400

    user = User.query.filter_by(email=email).first()

    if not user or not pwd_context.verify(password, user.password):
        return {"message": "Invalid email or password"}, 400

    access_token = create_access_token(identity=user.id)
    refresh_token = create_refresh_token(identity=user.id)
    # store token(s) in database
    add_token_to_db(access_token)
    add_token_to_db(refresh_token)


    return {"access_token": access_token, "refresh_token": refresh_token}, 200


# refresh tokens function
@auth_blueprint.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    user_id = get_jwt_identity()
    access_token = create_access_token(identity=user_id)
    # saving access and refresh tokens
    add_token_to_db(access_token)
    return {"access_token": access_token}, 200


# revoke access function
@auth_blueprint.route("/revoke_access", methods=["DELETE"])
@jwt_required()
def revoke_access_tk():
    jti = get_jwt()['jti']
    user_id = get_jwt_identity()
    revoke_token_from_db(jti, user_id)
    return {"message": "Access token revoked"}, 200


# revoke refresh function
@auth_blueprint.route("/revoke_refresh", methods=["DELETE"])
@jwt_required(refresh=True)
def revoke_refresh_tk():
    jti = get_jwt()['jti']
    user_id = get_jwt_identity()
    revoke_token_from_db(jti, user_id)
    return {"message": "Refresh token revoked"}, 200


@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    try:
        return is_token_revoked(jwt_payload)
    except Exception:
        return True


@jwt.user_lookup_loader
def load_user(jwt_header, jwt_payload):
    user_id = jwt_payload[cur_app.config['JWT_IDENTITY_CLAIM']]
    return User.query.get(user_id)


@auth_blueprint.errorhandler(ValidationError)
def validation_error(e):
    return jsonify(e.messages), 400

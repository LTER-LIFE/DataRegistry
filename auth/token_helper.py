from flask_jwt_extended import decode_token
from flask import current_app as app
from datetime import datetime

from sqlalchemy.exc import NoResultFound

from extensions import db
from website.models import TokenBlockList


# add the tokens to own table for easier management
def add_token_to_db(encoded_token):
    decoded_token = decode_token(encoded_token)
    jti = decoded_token['jti']
    token_type = decoded_token['type']
    # get the identity key from config
    user_id = decoded_token[app.config.get("JWT_IDENTITY_CLAIM")]
    expires_in = datetime.fromtimestamp(decoded_token['exp'])

    db_token = TokenBlockList(
        jti=jti,
        token_type=token_type,
        user_id=user_id,
        expires=expires_in,
    )

    db.session.add(db_token)
    db.session.commit()


# Revoking access from users
def revoke_token_from_db(token_jti, user_id):
    try:
        token = TokenBlockList.query.filter_by(jti=token_jti, user_id=user_id).one()
        token.revoked_on = datetime.utcnow()
        db.session.commit()
    except NoResultFound:
        raise Exception(f'Could not find the token for: {token_jti}')


def is_token_revoked(jwt_payload):
    jti = jwt_payload['jti']
    user_id = jwt_payload[app.config.get("JWT_IDENTITY_CLAIM")]
    try:
        token = TokenBlockList.query.filter_by(jti=jti, user_id=user_id).one()
        return token.revoked_on is not None
    except NoResultFound:
        raise Exception(f'Could not find the token for: {jti}')


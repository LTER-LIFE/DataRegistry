from extensions import db


class TokenBlockList(db.Model):
    tablename = 'token_block_list'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    jti = db.Column(db.String(36), nullable=False, unique=True)
    token_type = db.Column(db.String(15), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    revoked_on = db.Column(db.DateTime, nullable=True)
    expires = db.Column(db.DateTime, nullable=False)

    user = db.relationship('User')

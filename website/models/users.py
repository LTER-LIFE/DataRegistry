# ok

from sqlalchemy.ext.hybrid import hybrid_property

from extensions import db, pwd_context


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True)
    _password = db.Column(db.String(255), nullable=False)


    @hybrid_property
    def password(self):
        return self._password

    @password.setter
    def password(self, value):
        self._password = pwd_context.hash(value)

    roles = db.relationship('Role', secondary='user_roles', back_populates='users')

    def has_role(self, role):
        return bool(
            Role.query
            .join(Role.users)
            .filter(User.id == self.id)
            .filter(Role.slug == role)
            .count() == 1
        )


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(42), nullable=False)
    # the roles
    slug = db.Column(db.String(255), nullable=False, unique=True)
    users = db.relationship('User', secondary='user_roles', back_populates='roles')

# Pivot for users, as one user can have multiple roles
class UserRole(db.Model):
    __tablename__ = 'user_roles'
    # composite primary key (2 primary keys together)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), primary_key=True)


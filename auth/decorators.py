from functools import wraps

from flask import make_response
from flask_jwt_extended import get_current_user


# When called will check the role
def auth_role(role):
    def wrapper(func):
        @wraps(func)
        def decorator(*args, **kwargs):
            current_user = get_current_user()
            # if multiple roles leave as list otherwise make list
            roles = role if isinstance(role, list) else [role]
            # if user has no role
            if all(not current_user.has_role(r) for r in roles):
                return make_response({"message": "Missing any role."}, 403)
            return func(*args, **kwargs)
        return decorator

    return wrapper


# add to any class resource auth_role("admin" and "super-admin" and jwt_required() for
# endpoints
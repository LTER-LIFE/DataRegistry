from flask import request
from flask_restful import Resource, abort
from user_base import users
from website.models.users import User
from website.schemas.user_schema import UserSchema


# user for api list for get and post
class UserList(Resource):
    def get(self):
        users = User.query.all()
        schema = UserSchema(many=True)
        return {'results': schema.dump(users)}

    def post(self):
        data = request.get_json(force=True)
        last_user_id = users[-1].get('id')
        new_user = {'id': last_user_id + 1, **data}
        users.append(new_user)

        return {"msg": "user created"}


class UserResource(Resource):
    def get(self, user_id: int):
        user = next(filter(lambda u: u.get("id") == user_id, users), None)

        if user is None:
            abort(404)

        return user

    def put(self, user_id: int):
        data = request.get_json(force=True)
        user = None
        for i, u in enumerate(users):
            if u.get("id") == user_id:
                users[i] = {**u, **data}
                user = users[i]


        if user is None:
            abort(404)

        return {"msg": "user updated", "user": user}

    def delete(self, user_id: int):
        user = None

        for i, u in enumerate(users):
            if u.get("id") == user_id:
                user = u
                users.pop(i)

        if user is None:
            abort(404)

        return {"msg": "user deleted", "user": user}


from marshmallow.fields import String
from marshmallow import validate, validates_schema, ValidationError
from website import ma
from website.models.users import User


class UserSchema(ma.SQLAlchemyAutoSchema):
    name = String(required=True, validate=validate.Length(min=2, max=255),
                  error_messages={
                      "required": "Name is required.",
                      "invalid": "Name is invalid and needs to be a string"
                  })
    email = String(required=True, validate=validate.Email())

    @validates_schema
    def validate_email(self, data, **kwargs):
        email = data.get("email")
        if User.query.filter_by(email=email).count():
            raise ValidationError("Email already registered.")

    class Meta:
        model = User
        load_instance = True
        exclude = ["_password"]


class UserCreateSchema(UserSchema):
    pwd = String(required=True, validate=[
            validate.Regexp(r"^(?=.*[A-Z])(?=.*[!@#$&*])(?=.*[0-9])(?=.*[a-z]).{8,}$",
                            error="The password needs to be at least 8 characters long and include a lowercase, uppercase, number and special character.")
        ])

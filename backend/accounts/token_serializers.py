from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Accept email as the login identifier (username is stored as email)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"] = self.fields.pop(self.username_field)

    def validate(self, attrs):
        email = (attrs.pop("email", None) or attrs.pop(self.username_field, "")).lower()
        attrs[self.username_field] = email
        return super().validate(attrs)

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["email"] = user.email
        return token

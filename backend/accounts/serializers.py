from django.contrib.auth.models import User
from django.utils.text import slugify
from rest_framework import serializers

from .models import Organization, OrganizationMembership, Profile


class ProfileSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="user.id", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    primary_organization_id = serializers.PrimaryKeyRelatedField(
        source="primary_organization",
        queryset=Organization.objects.all(),
        required=False,
        allow_null=True,
    )
    primary_organization_name = serializers.CharField(
        source="primary_organization.name", read_only=True, allow_null=True
    )

    class Meta:
        model = Profile
        fields = (
            "id",
            "email",
            "full_name",
            "organization",
            "primary_organization_id",
            "primary_organization_name",
            "avatar_url",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "email",
            "primary_organization_name",
            "created_at",
            "updated_at",
        )


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=6, write_only=True)
    full_name = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    organization_name = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")

    def validate_email(self, value: str) -> str:
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def create(self, validated_data):
        email = validated_data["email"]
        password = validated_data["password"]
        full_name = validated_data.get("full_name", "")
        org_name = (validated_data.get("organization_name") or "").strip()

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=full_name,
        )
        profile = user.profile
        updates = []
        if full_name:
            profile.full_name = full_name
            updates.append("full_name")
        if org_name:
            profile.organization = org_name
            updates.append("organization")
            slug = slugify(org_name) or f"org-{user.id}"
            org, _ = Organization.objects.get_or_create(
                slug=slug,
                defaults={"name": org_name},
            )
            OrganizationMembership.objects.get_or_create(
                organization=org,
                user=user,
                defaults={"role": OrganizationMembership.Role.OWNER},
            )
            profile.primary_organization = org
            updates.append("primary_organization")
        if updates:
            profile.save(update_fields=[*updates, "updated_at"])
        return user


class OrganizationSerializer(serializers.ModelSerializer):
    my_role = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = ("id", "name", "slug", "my_role", "member_count", "created_at", "updated_at")
        read_only_fields = ("id", "slug", "my_role", "member_count", "created_at", "updated_at")

    def get_my_role(self, obj):
        user = self.context["request"].user
        m = obj.memberships.filter(user=user).first()
        return m.role if m else None

    def get_member_count(self, obj):
        return obj.memberships.count()


class OrganizationCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)

    def create(self, validated_data):
        user = self.context["request"].user
        name = validated_data["name"].strip()
        base = slugify(name) or "org"
        slug = base
        i = 1
        while Organization.objects.filter(slug=slug).exists():
            slug = f"{base}-{i}"
            i += 1
        org = Organization.objects.create(name=name, slug=slug)
        OrganizationMembership.objects.create(
            organization=org,
            user=user,
            role=OrganizationMembership.Role.OWNER,
        )
        profile = user.profile
        if not profile.primary_organization_id:
            profile.primary_organization = org
            profile.organization = name
            profile.save(update_fields=["primary_organization", "organization", "updated_at"])
        return org


class MembershipSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    full_name = serializers.CharField(source="user.profile.full_name", read_only=True)

    class Meta:
        model = OrganizationMembership
        fields = ("id", "user_id", "email", "full_name", "role", "created_at")
        read_only_fields = ("id", "user_id", "email", "full_name", "created_at")


class AddMemberSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(
        choices=OrganizationMembership.Role.choices,
        default=OrganizationMembership.Role.MEMBER,
    )

    def validate_email(self, value):
        try:
            return User.objects.get(email__iexact=value.lower())
        except User.DoesNotExist as exc:
            raise serializers.ValidationError("No user with that email.") from exc

    def create(self, validated_data):
        org = self.context["organization"]
        user = validated_data["email"]  # User instance from validate_email
        role = validated_data["role"]
        if role == OrganizationMembership.Role.OWNER:
            raise serializers.ValidationError({"role": "Cannot assign owner via invite; transfer ownership separately."})
        membership, created = OrganizationMembership.objects.update_or_create(
            organization=org,
            user=user,
            defaults={"role": role},
        )
        return membership

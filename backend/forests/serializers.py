from rest_framework import serializers

from accounts.models import Organization

from .models import BiomassHistory, Project, VerificationReport


class ProjectSerializer(serializers.ModelSerializer):
    owner_id = serializers.IntegerField(source="owner.id", read_only=True)
    organization_id = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.all(),
        source="organization",
        required=False,
        allow_null=True,
    )
    organization_name = serializers.CharField(
        source="organization.name", read_only=True, allow_null=True
    )
    # Optional: when posting satellite_agb_at_calibration with field_baseline, auto-set coeff
    satellite_agb_at_calibration = serializers.FloatField(
        required=False, allow_null=True, write_only=True
    )

    class Meta:
        model = Project
        fields = (
            "id",
            "name",
            "latitude",
            "longitude",
            "area_hectares",
            "owner_id",
            "organization_id",
            "organization_name",
            "field_baseline_agb_t_ha",
            "calibration_coefficient",
            "calibration_notes",
            "calibration_updated_at",
            "satellite_agb_at_calibration",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "owner_id",
            "organization_name",
            "calibration_updated_at",
            "created_at",
            "updated_at",
        )

    def update(self, instance, validated_data):
        sat = validated_data.pop("satellite_agb_at_calibration", None)
        field = validated_data.pop("field_baseline_agb_t_ha", serializers.empty)
        coeff = validated_data.pop("calibration_coefficient", serializers.empty)
        notes = validated_data.pop("calibration_notes", serializers.empty)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        needs_calib = (
            field is not serializers.empty
            or coeff is not serializers.empty
            or sat is not None
            or notes is not serializers.empty
        )
        if needs_calib:
            if field is not serializers.empty:
                instance.field_baseline_agb_t_ha = field
            if notes is not serializers.empty:
                instance.calibration_notes = notes or ""
            instance.save()
            instance.set_field_calibration(
                field_baseline_agb_t_ha=instance.field_baseline_agb_t_ha,
                satellite_agb_t_ha=sat,
                coefficient=None if coeff is serializers.empty else coeff,
                notes=instance.calibration_notes,
            )
        else:
            instance.save()
        return instance


class BiomassHistorySerializer(serializers.ModelSerializer):
    project_id = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all(),
        source="project",
    )

    class Meta:
        model = BiomassHistory
        fields = (
            "id",
            "project_id",
            "recorded_at",
            "carbon_density",
            "health_score",
            "source_url",
            "created_at",
        )
        read_only_fields = ("id", "recorded_at", "created_at")


class VerificationReportSerializer(serializers.ModelSerializer):
    project_id = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all(),
        source="project",
    )
    project_name = serializers.CharField(source="project.name", read_only=True)
    verifier_id = serializers.IntegerField(source="verifier.id", read_only=True, allow_null=True)

    class Meta:
        model = VerificationReport
        fields = (
            "id",
            "project_id",
            "project_name",
            "verifier_id",
            "status",
            "pdf_url",
            "integrity_seal_hash",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "project_name", "verifier_id", "created_at", "updated_at")

import hashlib
from datetime import timedelta
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import Organization, OrganizationMembership, Profile
from forests.models import BiomassHistory, Project, UserRole, VerificationReport


class Command(BaseCommand):
    help = "Seeds the database with initial users, organizations, community forests, biomass, and verifications."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Clear existing data before seeding",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("🌱 Starting database seeding..."))

        if options.get("reset"):
            self.stdout.write("Clearing existing data...")
            VerificationReport.objects.all().delete()
            BiomassHistory.objects.all().delete()
            Project.objects.all().delete()
            OrganizationMembership.objects.all().delete()
            Organization.objects.all().delete()
            UserRole.objects.all().delete()
            User.objects.exclude(is_superuser=True).delete()

        # 1. Create Users
        users_config = [
            {
                "username": "admin@terrai.org",
                "email": "admin@terrai.org",
                "password": "password123",
                "full_name": "Pema Sherpa",
                "org_name": "TerrAI Forest MRV",
                "is_staff": True,
                "is_superuser": True,
                "roles": [UserRole.Role.ADMIN, UserRole.Role.VALIDATOR, UserRole.Role.USER],
            },
            {
                "username": "validator@terrai.org",
                "email": "validator@terrai.org",
                "password": "password123",
                "full_name": "Dr. Bishnu Shrestha",
                "org_name": "Nepal Forestry Council & Verifiers",
                "is_staff": False,
                "is_superuser": False,
                "roles": [UserRole.Role.VALIDATOR, UserRole.Role.USER],
            },
            {
                "username": "demo@terrai.org",
                "email": "demo@terrai.org",
                "password": "password123",
                "full_name": "Sunita Tamang",
                "org_name": "Sundari Community Forest User Group",
                "is_staff": False,
                "is_superuser": False,
                "roles": [UserRole.Role.USER],
            },
        ]

        created_users = {}
        for uc in users_config:
            user, created = User.objects.get_or_create(
                username=uc["username"],
                defaults={
                    "email": uc["email"],
                    "is_staff": uc["is_staff"],
                    "is_superuser": uc["is_superuser"],
                },
            )
            user.set_password(uc["password"])
            user.email = uc["email"]
            user.first_name = uc["full_name"]
            user.is_staff = uc["is_staff"]
            user.is_superuser = uc["is_superuser"]
            user.save()

            profile = Profile.objects.get(user=user)
            profile.full_name = uc["full_name"]
            profile.organization = uc["org_name"]
            profile.save()

            for r in uc["roles"]:
                UserRole.objects.get_or_create(user=user, role=r)

            created_users[uc["email"]] = user
            status_text = "created" if created else "updated"
            self.stdout.write(f"  User {uc['email']} ({status_text})")

        admin_user = created_users["admin@terrai.org"]
        validator_user = created_users["validator@terrai.org"]
        demo_user = created_users["demo@terrai.org"]

        # 2. Create Organizations
        orgs_config = [
            {
                "name": "Sundari Community Forest User Group (CFUG)",
                "slug": "sundari-cfug",
                "members": [
                    (demo_user, OrganizationMembership.Role.OWNER),
                    (admin_user, OrganizationMembership.Role.MANAGER),
                ],
            },
            {
                "name": "Annapurna Conservation Area Alliance",
                "slug": "annapurna-alliance",
                "members": [
                    (admin_user, OrganizationMembership.Role.OWNER),
                    (validator_user, OrganizationMembership.Role.MEMBER),
                    (demo_user, OrganizationMembership.Role.MEMBER),
                ],
            },
            {
                "name": "Gorkha Watershed Forestry Network",
                "slug": "gorkha-network",
                "members": [
                    (admin_user, OrganizationMembership.Role.OWNER),
                    (demo_user, OrganizationMembership.Role.MANAGER),
                ],
            },
        ]

        created_orgs = {}
        for oc in orgs_config:
            org, _ = Organization.objects.get_or_create(
                slug=oc["slug"],
                defaults={"name": oc["name"]},
            )
            org.name = oc["name"]
            org.save()
            created_orgs[oc["slug"]] = org

            for u, role in oc["members"]:
                OrganizationMembership.objects.update_or_create(
                    organization=org,
                    user=u,
                    defaults={"role": role},
                )
            self.stdout.write(f"  Organization: {org.name}")

        # Set primary organizations on profiles
        demo_user.profile.primary_organization = created_orgs["sundari-cfug"]
        demo_user.profile.save()
        admin_user.profile.primary_organization = created_orgs["annapurna-alliance"]
        admin_user.profile.save()

        # 3. Create Projects
        projects_data = [
            {
                "name": "Sundari Jal Community Forest",
                "latitude": 27.8012,
                "longitude": 85.4215,
                "area_hectares": 245.5,
                "owner": demo_user,
                "organization": created_orgs["sundari-cfug"],
                "field_baseline_agb_t_ha": 142.3,
                "calibration_coefficient": 1.08,
                "calibration_notes": "Calibrated against 2024 CFUG sample plot survey (DBH > 10cm).",
                "biomass_history": [
                    {"months_ago": 10, "carbon_density": 138.2, "health_score": 0.81},
                    {"months_ago": 7, "carbon_density": 140.5, "health_score": 0.83},
                    {"months_ago": 4, "carbon_density": 142.1, "health_score": 0.85},
                    {"months_ago": 1, "carbon_density": 145.4, "health_score": 0.88},
                ],
                "verification": {
                    "status": VerificationReport.Status.APPROVED,
                    "verifier": validator_user,
                    "seal": hashlib.sha256(b"sundari-jal-approved-2024").hexdigest()[:32],
                },
            },
            {
                "name": "Gorkha Hill Community Forest",
                "latitude": 28.0050,
                "longitude": 84.6290,
                "area_hectares": 512.0,
                "owner": admin_user,
                "organization": created_orgs["gorkha-network"],
                "field_baseline_agb_t_ha": 168.0,
                "calibration_coefficient": 0.95,
                "calibration_notes": "DFO verified sample plots from seasonal inventory.",
                "biomass_history": [
                    {"months_ago": 9, "carbon_density": 160.0, "health_score": 0.79},
                    {"months_ago": 6, "carbon_density": 164.2, "health_score": 0.82},
                    {"months_ago": 3, "carbon_density": 167.8, "health_score": 0.84},
                    {"months_ago": 1, "carbon_density": 170.1, "health_score": 0.86},
                ],
                "verification": {
                    "status": VerificationReport.Status.APPROVED,
                    "verifier": validator_user,
                    "seal": hashlib.sha256(b"gorkha-approved-2024").hexdigest()[:32],
                },
            },
            {
                "name": "Chitwan Buffer Zone Sal Forest",
                "latitude": 27.5291,
                "longitude": 84.4533,
                "area_hectares": 820.0,
                "owner": demo_user,
                "organization": created_orgs["sundari-cfug"],
                "field_baseline_agb_t_ha": 215.4,
                "calibration_coefficient": 1.02,
                "calibration_notes": "Terai Arc Landscape allometric survey 2023.",
                "biomass_history": [
                    {"months_ago": 8, "carbon_density": 210.1, "health_score": 0.87},
                    {"months_ago": 5, "carbon_density": 212.8, "health_score": 0.89},
                    {"months_ago": 2, "carbon_density": 215.4, "health_score": 0.91},
                ],
                "verification": {
                    "status": VerificationReport.Status.PENDING,
                    "verifier": None,
                    "seal": None,
                },
            },
            {
                "name": "Lalitpur Southern Ridge Forest",
                "latitude": 27.5850,
                "longitude": 85.3350,
                "area_hectares": 180.2,
                "owner": admin_user,
                "organization": created_orgs["annapurna-alliance"],
                "field_baseline_agb_t_ha": 135.0,
                "calibration_coefficient": 1.0,
                "calibration_notes": "Baseline established from regional temperate mixed forest table.",
                "biomass_history": [
                    {"months_ago": 6, "carbon_density": 131.0, "health_score": 0.77},
                    {"months_ago": 3, "carbon_density": 133.5, "health_score": 0.79},
                    {"months_ago": 1, "carbon_density": 135.0, "health_score": 0.80},
                ],
                "verification": {
                    "status": VerificationReport.Status.PENDING,
                    "verifier": None,
                    "seal": None,
                },
            },
            {
                "name": "Annapurna Oak-Rhododendron Reserve",
                "latitude": 28.4500,
                "longitude": 83.8500,
                "area_hectares": 640.0,
                "owner": admin_user,
                "organization": created_orgs["annapurna-alliance"],
                "field_baseline_agb_t_ha": 195.2,
                "calibration_coefficient": 1.05,
                "calibration_notes": "High elevation temperate Rhododendron-Quercus belt inventory.",
                "biomass_history": [
                    {"months_ago": 11, "carbon_density": 188.0, "health_score": 0.84},
                    {"months_ago": 7, "carbon_density": 191.4, "health_score": 0.86},
                    {"months_ago": 4, "carbon_density": 193.9, "health_score": 0.88},
                    {"months_ago": 1, "carbon_density": 196.2, "health_score": 0.90},
                ],
                "verification": {
                    "status": VerificationReport.Status.APPROVED,
                    "verifier": validator_user,
                    "seal": hashlib.sha256(b"annapurna-approved-2024").hexdigest()[:32],
                },
            },
        ]

        now = timezone.now()
        for pdata in projects_data:
            project, _ = Project.objects.update_or_create(
                name=pdata["name"],
                defaults={
                    "latitude": pdata["latitude"],
                    "longitude": pdata["longitude"],
                    "area_hectares": pdata["area_hectares"],
                    "owner": pdata["owner"],
                    "organization": pdata["organization"],
                    "field_baseline_agb_t_ha": pdata["field_baseline_agb_t_ha"],
                    "calibration_coefficient": pdata["calibration_coefficient"],
                    "calibration_notes": pdata["calibration_notes"],
                    "calibration_updated_at": now,
                },
            )
            self.stdout.write(f"  Project: {project.name} ({project.area_hectares} ha)")

            # Biomass history
            if not project.biomass_entries.exists():
                for bentry in pdata["biomass_history"]:
                    rec_time = now - timedelta(days=bentry["months_ago"] * 30)
                    entry = BiomassHistory.objects.create(
                        project=project,
                        carbon_density=bentry["carbon_density"],
                        health_score=bentry["health_score"],
                    )
                    BiomassHistory.objects.filter(pk=entry.pk).update(recorded_at=rec_time)

            # Verification Report
            vdata = pdata["verification"]
            VerificationReport.objects.update_or_create(
                project=project,
                defaults={
                    "status": vdata["status"],
                    "verifier": vdata["verifier"],
                    "integrity_seal_hash": vdata["seal"],
                },
            )

        self.stdout.write(self.style.SUCCESS(" Database seeded successfully!"))
        self.stdout.write(self.style.SUCCESS("Credentials for testing:"))
        self.stdout.write("  Admin:     admin@terrai.org     / password123")
        self.stdout.write("  Validator: validator@terrai.org / password123")
        self.stdout.write("  Demo CFUG: demo@terrai.org      / password123")

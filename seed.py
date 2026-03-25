"""
Seed script for FitScore - Creates test data for development and testing.
Usage: python seed.py
"""

import random
from datetime import date, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from auth import get_password_hash
from config import DATABASE_URL_SYNC, WODTypes
from database import Base
from models import WOD, Athlete, Competition, Score, User, WODStandard

# Create sync engine and session
engine = create_engine(DATABASE_URL_SYNC)
SessionLocal = sessionmaker(bind=engine)


def seed_database():
    """Main seed function."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        # Check if data already exists
        existing_users = db.query(User).count()
        if existing_users > 0:
            print("Database already has data. Skipping seed.")
            print("To reset, delete fitscore.db and run again.")
            return

        print("Seeding database...")

        # ============== Create Users ==============
        print("Creating users...")

        admin = User(
            username="admin",
            email="admin@fitscore.com",
            password_hash=get_password_hash("admin123"),
            full_name="Administrador",
            role="admin",
        )
        db.add(admin)

        judge1 = User(
            username="judge1",
            email="judge1@fitscore.com",
            password_hash=get_password_hash("judge123"),
            full_name="Juan Juez",
            role="judge",
        )
        db.add(judge1)

        judge2 = User(
            username="judge2",
            email="judge2@fitscore.com",
            password_hash=get_password_hash("judge123"),
            full_name="Maria Juez",
            role="judge",
        )
        db.add(judge2)

        viewer = User(
            username="viewer",
            email="viewer@fitscore.com",
            password_hash=get_password_hash("viewer123"),
            full_name="Espectador",
            role="viewer",
        )
        db.add(viewer)

        db.commit()
        print("  Created 4 users")

        # ============== Create Competition ==============
        print("Creating competition...")

        competition = Competition(
            name="Copa Box Championship 2025",
            description=(
                "Competencia regional de CrossFit con atletas de toda la region"
            ),
            date=date.today() + timedelta(days=7),
            location="CrossFit Central Box",
            is_active=True,
            created_by=admin.id,
        )
        db.add(competition)
        db.commit()
        print(f"  Created competition: {competition.name}")

        # ============== Create WODs ==============
        print("Creating WODs...")

        wods_data = [
            {
                "name": "The Ladder",
                "description": "21-15-9: Thrusters + Pull-ups",
                "wod_type": WODTypes.TIME,
                "time_cap": 900,  # 15 minutes
                "order": 1,
            },
            {
                "name": "Heavy Grace",
                "description": "30 Clean & Jerks for time",
                "wod_type": WODTypes.TIME,
                "time_cap": 600,  # 10 minutes
                "order": 2,
            },
            {
                "name": "AMRAP Madness",
                "description": (
                    "12 min AMRAP: 5 Deadlifts + 10 Box Jumps + 15 Wall Balls"
                ),
                "wod_type": WODTypes.AMRAP,
                "time_cap": 720,  # 12 minutes
                "order": 3,
            },
            {
                "name": "Max Snatch",
                "description": "Find your 1RM Snatch in 12 minutes",
                "wod_type": WODTypes.LOAD,
                "time_cap": 720,
                "order": 4,
            },
        ]

        wods = []
        for wod_data in wods_data:
            wod = WOD(
                name=wod_data["name"],
                description=wod_data["description"],
                wod_type=wod_data["wod_type"],
                time_cap=wod_data["time_cap"],
                order_in_competition=wod_data["order"],
                competition_id=competition.id,
            )
            db.add(wod)
            wods.append(wod)

        db.commit()
        print(f"  Created {len(wods)} WODs")

        # Add WOD Standards
        print("Adding WOD standards...")

        # Standards for different divisions (weights in kg)
        standards_map = {
            "RX Masculino": {"wod1": 43, "wod2": 61, "wod3": 70, "wod4": None},
            "RX Femenino": {"wod1": 29, "wod2": 43, "wod3": 47, "wod4": None},
            "Scaled Masculino": {"wod1": 29, "wod2": 43, "wod3": 47, "wod4": None},
            "Scaled Femenino": {"wod1": 20, "wod2": 29, "wod3": 34, "wod4": None},
            "Master +40 Masculino": {"wod1": 34, "wod2": 52, "wod3": 61, "wod4": None},
            "Master +40 Femenino": {"wod1": 25, "wod2": 38, "wod3": 43, "wod4": None},
        }

        for division, weights in standards_map.items():
            for i, wod in enumerate(wods):
                weight_key = f"wod{i+1}"
                if weights.get(weight_key):
                    standard = WODStandard(
                        wod_id=wod.id,
                        division=division,
                        rx_weight_kg=weights[weight_key],
                    )
                    db.add(standard)

        db.commit()
        print("  Added WOD standards")

        # ============== Create Athletes ==============
        print("Creating athletes...")

        # Names for generating athletes
        male_names = [
            "Carlos",
            "Miguel",
            "Juan",
            "Pedro",
            "Luis",
            "Diego",
            "Andres",
            "Fernando",
            "Ricardo",
            "Eduardo",
            "Alejandro",
            "Sebastian",
            "Daniel",
            "Pablo",
            "Mateo",
            "Jorge",
            "Martin",
            "Nicolas",
            "David",
            "Gabriel",
            "Roberto",
            "Javier",
            "Oscar",
            "Adrian",
            "Ivan",
            "Hugo",
            "Mario",
            "Sergio",
            "Manuel",
            "Rafael",
        ]
        female_names = [
            "Maria",
            "Ana",
            "Carmen",
            "Laura",
            "Sofia",
            "Isabella",
            "Valentina",
            "Lucia",
            "Camila",
            "Paula",
            "Andrea",
            "Diana",
            "Gabriela",
            "Victoria",
            "Natalia",
            "Elena",
            "Rosa",
            "Teresa",
            "Patricia",
            "Monica",
            "Carolina",
            "Alejandra",
            "Daniela",
            "Mariana",
            "Fernanda",
            "Paola",
            "Lorena",
            "Sandra",
            "Gloria",
            "Julia",
        ]
        last_names = [
            "Garcia",
            "Rodriguez",
            "Martinez",
            "Lopez",
            "Gonzalez",
            "Hernandez",
            "Perez",
            "Sanchez",
            "Ramirez",
            "Torres",
            "Flores",
            "Rivera",
            "Gomez",
            "Diaz",
            "Cruz",
            "Morales",
            "Ortiz",
            "Gutierrez",
            "Chavez",
            "Ramos",
            "Vargas",
            "Castillo",
            "Jimenez",
            "Mendoza",
            "Ruiz",
            "Alvarez",
            "Romero",
            "Medina",
            "Aguilar",
            "Castro",
        ]
        boxes = [
            "CrossFit Central",
            "CrossFit Norte",
            "CrossFit Sur",
            "Box Fitness Elite",
            "Functional Training",
            "CrossFit Power",
            "Box Warriors",
            "CrossFit Evolution",
            "Garage Box",
            "CrossFit United",
            None,
            None,  # Some athletes might not have a box
        ]

        athletes = []
        bib_counter = 1

        # Create 5 athletes per division (50 total)
        active_divisions = [
            "RX Masculino",
            "RX Femenino",
            "Scaled Masculino",
            "Scaled Femenino",
            "Master +40 Masculino",
            "Master +40 Femenino",
            "Master +50 Masculino",
            "Master +50 Femenino",
            "Novato Masculino",
            "Novato Femenino",
        ]

        for division in active_divisions:
            is_male = "Masculino" in division
            is_master40 = "+40" in division
            is_master50 = "+50" in division
            is_teen = "Novato" in division

            for _ in range(5):
                # Generate birth date based on category
                if is_teen:
                    age = random.randint(14, 17)
                elif is_master50:
                    age = random.randint(50, 60)
                elif is_master40:
                    age = random.randint(40, 49)
                else:
                    age = random.randint(18, 39)

                birth_year = date.today().year - age
                birth_date = date(
                    birth_year, random.randint(1, 12), random.randint(1, 28)
                )

                first_name = random.choice(male_names if is_male else female_names)
                last_name = random.choice(last_names)
                name = f"{first_name} {last_name}"

                athlete = Athlete(
                    name=name,
                    gender="Masculino" if is_male else "Femenino",
                    birth_date=birth_date,
                    division=division,
                    box=random.choice(boxes),
                    email=f"{first_name.lower()}.{last_name.lower()}@email.com",
                    bib_number=str(bib_counter).zfill(3),
                    competition_id=competition.id,
                )
                db.add(athlete)
                athletes.append(athlete)
                bib_counter += 1

        db.commit()
        print(f"  Created {len(athletes)} athletes")

        # ============== Create Scores ==============
        print("Creating scores...")

        # Group athletes by division
        athletes_by_division = {}
        for athlete in athletes:
            if athlete.division not in athletes_by_division:
                athletes_by_division[athlete.division] = []
            athletes_by_division[athlete.division].append(athlete)

        scores_created = 0

        for division, div_athletes in athletes_by_division.items():
            for wod in wods:
                # Generate scores for this division in this WOD
                for athlete in div_athletes:
                    # 90% chance of having a valid score, 10% no result
                    if random.random() < 0.9:
                        if wod.wod_type == WODTypes.TIME:
                            raw_result = random.randint(
                                180, min(wod.time_cap - 60, 840)
                            )
                        elif wod.wod_type == WODTypes.AMRAP:
                            raw_result = random.randint(100, 250)
                        elif wod.wod_type == WODTypes.LOAD:
                            is_male = "Masculino" in division
                            if is_male:
                                raw_result = random.randint(60, 130)
                            else:
                                raw_result = random.randint(40, 85)
                        else:
                            raw_result = random.randint(50, 150)
                    else:
                        raw_result = None

                    score = Score(
                        athlete_id=athlete.id,
                        wod_id=wod.id,
                        raw_result=raw_result,
                        tiebreak=(
                            random.randint(30, 300)
                            if wod.wod_type == WODTypes.AMRAP and raw_result
                            else None
                        ),
                        status="verified" if random.random() > 0.3 else "pending",
                        judge_id=random.choice([judge1.id, judge2.id]),
                        submitted_at=datetime.utcnow()
                        - timedelta(hours=random.randint(1, 48)),
                    )
                    db.add(score)
                    scores_created += 1

        db.commit()
        print(f"  Created {scores_created} scores")

        # ============== Calculate Rankings ==============
        print("Calculating rankings and points...")

        # For each WOD, calculate rankings
        for wod in wods:
            # Get all scores for this WOD grouped by division
            wod_scores = (
                db.query(Score).join(Athlete).filter(Score.wod_id == wod.id).all()
            )

            # Group by division
            scores_by_div = {}
            for score in wod_scores:
                athlete = db.query(Athlete).get(score.athlete_id)
                div = athlete.division
                if div not in scores_by_div:
                    scores_by_div[div] = []
                scores_by_div[div].append(score)

            # Calculate rankings for each division
            for div, div_scores in scores_by_div.items():
                # Sort scores
                valid_scores = [s for s in div_scores if s.raw_result is not None]
                invalid_scores = [s for s in div_scores if s.raw_result is None]

                # Sort based on WOD type
                if wod.wod_type == WODTypes.TIME:
                    valid_scores.sort(
                        key=lambda s: (s.raw_result, s.tiebreak or float("inf"))
                    )
                else:  # Higher is better
                    valid_scores.sort(
                        key=lambda s: (-s.raw_result, s.tiebreak or float("inf"))
                    )

                # Assign ranks and points
                total_athletes = len(div_scores)
                current_rank = 1

                for i, score in enumerate(valid_scores):
                    if i > 0:
                        prev = valid_scores[i - 1]
                        if (
                            score.raw_result != prev.raw_result
                            or score.tiebreak != prev.tiebreak
                        ):
                            current_rank = i + 1
                    score.rank = current_rank
                    score.points = total_athletes - current_rank + 1

                # No result = 0 points
                for score in invalid_scores:
                    score.rank = len(valid_scores) + 1
                    score.points = 0

        db.commit()
        print("  Rankings calculated")

        # ============== Summary ==============
        print("\n" + "=" * 50)
        print("SEED COMPLETED SUCCESSFULLY!")
        print("=" * 50)
        print("\nTest Credentials:")
        print("  Admin:  admin / admin123")
        print("  Judge1: judge1 / judge123")
        print("  Judge2: judge2 / judge123")
        print("  Viewer: viewer / viewer123")
        print("\nData Created:")
        print(f"  Competition: {competition.name}")
        print(f"  WODs: {len(wods)}")
        print(f"  Athletes: {len(athletes)}")
        print(f"  Scores: {scores_created}")
        print(f"  Divisions: {len(active_divisions)}")
        print("\nRun the application with:")
        print("  uvicorn main:app --reload")
        print("  or: python main.py")
        print("\nAccess at: http://localhost:8000")
        print("=" * 50)


if __name__ == "__main__":
    seed_database()

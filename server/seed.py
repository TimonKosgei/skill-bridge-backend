from faker import Faker 
from database import db
from models import User, Course
from app import app

fake = Faker()
with app.app_context():
    for _ in range(10):
        user = User(
            username=fake.user_name(),
            email=fake.email(),
            password=fake.password(),
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            profile_picture_url=fake.image_url(),
            bio=fake.text(),
            role=fake.random_element(elements=('student', 'instructor')),
            registration_date=fake.date_time_this_decade()
        )
        db.session.add(user)
        db.session.commit()
    for _ in range(5):
        course = Course(
            instructor=user,
            title=fake.sentence(),
            description=fake.text(),
            category=fake.random_element(elements=('programming', 'design', 'business')),
            creation_date=fake.date_time_this_decade(),
            last_update=fake.date_time_this_decade(),
            course_image_url=fake.image_url(),
            is_published=fake.boolean(chance_of_getting_true=80)
        )
        db.session.add(course)
        db.session.commit()
    print("Database seeded!")


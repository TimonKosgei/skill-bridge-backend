from app import app  # Import your Flask app
from database import db
from models import Course  # Import your Course model

# Run inside application context
with app.app_context():
    db.session.query(Course).delete()
    db.session.commit()

print("All courses deleted successfully!")

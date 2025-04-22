from app import app  # Import your Flask app
from database import db
from models import UserBadge  # Import your Course model

# Run inside application context
with app.app_context():
    db.session.query(UserBadge).delete()
    db.session.commit()

print("All courses deleted successfully!")

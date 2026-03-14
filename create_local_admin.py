from app import app, db, User
import os

with app.app_context():
    # Ensure tables exist
    db.create_all()
    
    # Check if user exists
    email = "carlos.casabianca@yahoo.com"
    user = User.query.filter_by(email=email).first()
    
    if not user:
        print(f"Creating local offline admin account for {email}...")
        user = User(email=email, role="admin")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()
        print("Success! You can now log into localhost:5000 with password: password123")
    else:
        print("User already exists in the local database. You can log in!")

from flask_sqlalchemy import SQLAlchemy

# Initialize the database instance
db = SQLAlchemy()

# Define the Apartment model
class Apartment(db.Model):
    __tablename__ = 'apartments'

    id = db.Column(db.Integer, primary_key=True)  # Primary key
    title = db.Column(db.String(120), nullable=False)  # Apartment title
    description = db.Column(db.Text, nullable=True)  # Description of the apartment
    location = db.Column(db.String(120), nullable=False)  # Apartment location
    rent = db.Column(db.Float, nullable=False)  # Rent per month
    owner_id = db.Column(db.Integer, db.ForeignKey('property_owners.id'), nullable=False)  # Foreign key for the owner

    # Define the relationship to the Owner model
    owner = db.relationship('Owner', backref=db.backref('apartments', lazy=True))

    def __repr__(self):
        return f"<Apartment {self.title}>"

# Define the Owner model
class Owner(db.Model):
    __tablename__ = 'property_owners'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # Auto-incremented primary key
    number = db.Column(db.String, nullable=False)  # Owner's contact number
    username = db.Column(db.String, unique=True, nullable=False)  # Unique username
    hash = db.Column(db.String, nullable=False)  # Hashed password

    def __repr__(self):
        return f"<Owner {self.username}>"

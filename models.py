# models.py
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import secrets

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    user_type = db.Column(db.String(20), nullable=False)  # 'student' or 'company'
    
    # Student fields
    full_name = db.Column(db.String(100))
    mobile = db.Column(db.String(20))
    college = db.Column(db.String(200))
    course = db.Column(db.String(100))
    graduation_year = db.Column(db.Integer)
    skills = db.Column(db.Text)
    about_self = db.Column(db.Text)
    resume_url = db.Column(db.String(500))
    portfolio_url = db.Column(db.String(500))
    profile_picture = db.Column(db.String(500))
    
    # Company fields - All fields made nullable for registration
    company_name = db.Column(db.String(200))
    industry = db.Column(db.String(100))
    company_size = db.Column(db.String(50))
    website = db.Column(db.String(200))
    description = db.Column(db.Text)
    location = db.Column(db.String(200))
    contact_person = db.Column(db.String(100))
    
    # Social links
    linkedin = db.Column(db.String(200))
    github = db.Column(db.String(200))
    leetcode = db.Column(db.String(200))
    hackerrank = db.Column(db.String(200))
    
    # Password reset
    reset_token = db.Column(db.String(100), unique=True)
    reset_token_expiry = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    internships = db.relationship('Internship', backref='company', lazy=True, foreign_keys='Internship.company_id')
    applications = db.relationship('Application', backref='student', lazy=True, foreign_keys='Application.student_id')
    certificates = db.relationship('Certificate', backref='student', lazy=True)
    notifications = db.relationship('Notification', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def generate_reset_token(self):
        self.reset_token = secrets.token_urlsafe(32)
        self.reset_token_expiry = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        return self.reset_token

    def to_dict(self):
        """Convert user to dictionary for API responses"""
        base_data = {
            "id": self.id,
            "email": self.email,
            "user_type": self.user_type,
            "full_name": self.full_name,
            "mobile": self.mobile,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
        
        if self.user_type == "student":
            base_data.update({
                "college": self.college,
                "course": self.course,
                "graduation_year": self.graduation_year,
                "skills": self.skills,
                "about_self": self.about_self,
                "resume_url": self.resume_url,
                "portfolio_url": self.portfolio_url,
                "profile_picture": self.profile_picture,
                "social_links": {
                    "linkedin": self.linkedin,
                    "github": self.github,
                    "leetcode": self.leetcode,
                    "hackerrank": self.hackerrank
                }
            })
        elif self.user_type == "company":
            base_data.update({
                "company_name": self.company_name,
                "industry": self.industry,
                "company_size": self.company_size,
                "website": self.website,
                "description": self.description,
                "location": self.location,
                "contact_person": self.contact_person,
                "social_links": {
                    "linkedin": self.linkedin,
                    "github": self.github
                }
            })
        
        return base_data

# Update the Internship model in models.py
class Internship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    requirements = db.Column(db.Text, nullable=False)
    skills_required = db.Column(db.Text)
    internship_type = db.Column(db.String(50))
    location = db.Column(db.String(100))
    salary = db.Column(db.String(100))
    duration = db.Column(db.String(50))
    work_mode = db.Column(db.String(20), default='remote')  # remote, onsite, hybrid
    start_date = db.Column(db.DateTime)
    deadline = db.Column(db.DateTime)
    responsibilities = db.Column(db.Text)
    learning_outcomes = db.Column(db.Text)
    education_level = db.Column(db.String(50))
    experience_level = db.Column(db.String(50))
    openings = db.Column(db.Integer, default=1)
    is_active = db.Column(db.Boolean, default=True)
    is_published = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    applications = db.relationship('Application', backref='internship', lazy=True)

class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    internship_id = db.Column(db.Integer, db.ForeignKey('internship.id'), nullable=False)
    cover_letter = db.Column(db.Text)
    status = db.Column(db.String(50), default='applied')  # applied, reviewed, approved, rejected, interview, offered
    applied_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class Certificate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    file_url = db.Column(db.String(500), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50), default='general')  # general, application, application_status, application_withdrawn
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
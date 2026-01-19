from app.extensions import db
from flask_login import UserMixin
from datetime import datetime, timezone, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

# Get the current UTC time
utc_now = datetime.now(timezone.utc)

# Add 1 hour to UTC time for UTC+1 (Berlin Standard Time)
berlin_time = utc_now + timedelta(hours=1)


class User(UserMixin, db.Model):
    """
    User model for storing user details and authentication information.
    """
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    password_hash = db.Column(db.String(256))
    conversations = db.relationship('Conversation', backref='user', lazy=True, cascade='all, delete-orphan')
    settings = db.Column(db.JSON)  # Store user-specific settings
    
    def set_password(self, password):
        """Hash and set the user's password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if the provided password matches the stored hash."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"


class Conversation(db.Model):
    """
    Conversation model for grouping messages.
    """
    __tablename__ = 'conversation'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), default='New Conversation')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    messages = db.relationship('Message', backref='conversation', lazy=True, cascade='all, delete-orphan')
    created_at = db.Column(db.DateTime, default=berlin_time)

    def generate_title(self):
        """Generate a title based on the first message and the creation date."""
        if self.messages:
            first_message = self.messages[0].content
            # Limit the message content for the title to 30 characters
            snippet = first_message[:30].strip() + ('...' if len(first_message) > 30 else '...')
        else:
            snippet = "New Conversation"
        
        # Append the date and time of creation
        formatted_date = self.created_at.strftime('%Y-%m-%d %H:%M')
        return f"{snippet} - {formatted_date}"

    def set_title(self):
        """Set the title dynamically based on the first message and creation date."""
        if self.messages:
            # Generate title based on the first message
            self.title = self.generate_title()
        else:
            # Default title if no messages exist
            self.title = "New Conversation"

    def __repr__(self):
        return f"<Conversation {self.id} by User {self.user_id}>"



class Message(db.Model):
    """
    Message model for storing individual chat messages.
    """
    __tablename__ = 'message'
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(10), nullable=False)  # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=berlin_time)

    def __repr__(self):
        return f"<Message {self.id} in Conversation {self.conversation_id}>"


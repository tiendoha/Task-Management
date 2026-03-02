import string
import random

def generate_random_password(length=10):
    """Generates a random password with mixed character types."""
    if length < 6:
        length = 6
        
    uppercase = string.ascii_uppercase
    lowercase = string.ascii_lowercase
    digits = string.digits
    special = "!@#$%^&*"
    
    # Ensure at least one of each type
    password = [
        random.choice(uppercase),
        random.choice(lowercase),
        random.choice(digits),
        random.choice(special)
    ]
    
    # Fill the rest randomly
    all_chars = uppercase + lowercase + digits + special
    password += [random.choice(all_chars) for _ in range(length - 4)]
    
    # Shuffle for randomness
    random.shuffle(password)
    return "".join(password)

import os
from flask_mail import Mail, Message

mail = Mail()

def init_mail(app):
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'nanotech.hrm@gmail.com')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    
    mail.init_app(app)

def send_reset_email(to_email, new_password):
    if not to_email:
        return
        
    sender = os.environ.get('MAIL_USERNAME', 'nanotech.hrm@gmail.com')
    msg = Message("HRM FaceID - Your Password Has Been Reset",
                  sender=sender,
                  recipients=[to_email])
    
    msg.body = f"""
    Hello,

    Your administrator has reset your password for the HRM FaceID system.
    
    Your new temporary password is: {new_password}
    
    Please log in with this temporary password. You will be prompted to change it immediately to ensure your account security.

    Regards,
    HRM Administrator
    """
    
    try:
        mail.send(msg)
        print(f"Password reset email sent to {to_email}")
    except Exception as e:
        print(f"Failed to send email to {to_email}: {str(e)}")

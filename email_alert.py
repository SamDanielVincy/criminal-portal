# email_alert.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time

curr_time = time.strftime("%H:%M:%S", time.localtime())

def send_email_alert(criminal_id, criminal_info):
    sender_email = "sivaneswaran020604@gmail.com"
    receiver_email = "as143sivalove@gmail.com .com"
    loc ="Ariyur"
    app_password = "nroj evrd vlta kdyn"  # Your app password

    curr_time1 = time.strftime("%H:%M:%S", time.localtime())



    
    subject = f"⚠️ Criminal Detected - ID: {criminal_id}"
    body = f"""
    A criminal has been detected by the Flask AI Surveillance System.

    ➤ Criminal ID: {criminal_id}
    ➤ Name: {criminal_info.get('name', 'Unknown')}
    ➤ Crime: {criminal_info.get('crime', 'Not specified')}
    ➤ Last Seen: {criminal_info.get('last_seen', 'Unknown')}
    ➤ Located At: {loc}
    ➤ Seen at: {curr_time}
    



    Please take immediate action.
    """

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, app_password)
        server.send_message(msg)
        server.quit()
        print("✅ Alert email sent successfully!")
        return True
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False

import json
from http import HTTPStatus
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate
from smtplib import SMTP, SMTPRecipientsRefused

def send_email(to, subject, body):
    message = MIMEMultipart()
    message["From"] = "noreply@example.com"
    message["To"] = to
    message["Subject"] = subject
    message["Date"] = formatdate(localtime=True)
    message.attach(MIMEText(body, "plain"))
    
    with SMTP("smtp.example.com") as smtp:
        smtp.send_message(message)
        
def handle_request(request):
    if request.method != "POST":
        return (HTTPStatus.METHOD_NOT_ALLOWED, {})
    
    data = json.loads(request.body)
    subject = data["subject"]
    body = data["body"]
    format = data["format"]
    transform_script = data.get("transform_script")
    
    if not (format == "html" or format == "text"):
        return (HTTPStatus.BAD_REQUEST, {})
        
    if transform_script:
        # TODO: Implement script evaluation in a restricted environment
        pass
    
    if format == "html":
        body = escape(body)
    
    send_email("recipient@example.com", subject, body)
    
    return (HTTPStatus.OK, {})
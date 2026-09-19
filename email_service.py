import os, smtplib, logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

log = logging.getLogger('email_service')

SUPPORT_EMAIL = os.environ.get('SUPPORT_EMAIL', 'support@thesmartmag.com')
CONTACT_EMAIL = os.environ.get('CONTACT_EMAIL', 'contact@thesmartmag.com')
QUERY_EMAIL = os.environ.get('QUERY_EMAIL', 'query@thesmartmag.com')

SMTP_HOST = os.environ.get('SMTP_HOST', '')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
SMTP_USER = os.environ.get('SMTP_USER', '')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
SMTP_USE_TLS = os.environ.get('SMTP_USE_TLS', 'true').lower() in ('true', '1', 'yes')

def _send_email(from_addr, to_addr, subject, html_body, text_body=''):
    if not SMTP_HOST or not SMTP_USER:
        log.info('SMTP not configured in environment. [MOCK EMAIL DISPATCHED] From: %s | To: %s | Subject: %s', from_addr, to_addr, subject)
        return True
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = 'TheSmartMag Quant Network <' + from_addr + '>'
        msg['To'] = to_addr
        msg['Reply-To'] = from_addr
        if text_body:
            msg.attach(MIMEText(text_body, 'plain'))
        msg.attach(MIMEText(html_body, 'html'))
        if SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=12)
        else:
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=12)
            if SMTP_USE_TLS:
                server.starttls()
        if SMTP_USER and SMTP_PASSWORD:
            server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(from_addr, [to_addr], msg.as_string())
        server.quit()
        log.info('Email sent successfully to %s (Subject: %s)', to_addr, subject)
        return True
    except Exception as e:
        log.error('Failed to send email to %s: %s', to_addr, e)
        return False

def get_base_html_template(title, content_html, sender_footer='support@thesmartmag.com'):
    return '''<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>''' + title + '''</title>
  <style>
    body { margin:0; padding:0; background-color:#020812; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; color:#e2e8f0; }
    .container { max-width:600px; margin:28px auto; background:#060e1d; border:1px solid #00f090; border-radius:12px; overflow:hidden; box-shadow:0 12px 48px rgba(0,0,0,0.85); }
    .header { background:linear-gradient(135deg,#091a33,#020812); padding:26px 24px; text-align:center; border-bottom:1px solid rgba(0,240,144,0.35); }
    .header h1 { margin:0; color:#00f090; font-size:21px; font-weight:800; letter-spacing:1.5px; }
    .content { padding:30px 24px; line-height:1.65; font-size:14.5px; color:#cbd5e1; }
    .badge { display:inline-block; background:rgba(0,240,144,0.15); border:1px solid #00f090; color:#00f090; padding:4px 12px; border-radius:4px; font-weight:700; font-size:11px; }
    .badge-alert { display:inline-block; background:rgba(255,184,0,0.15); border:1px solid #ffb800; color:#ffb800; padding:4px 12px; border-radius:4px; font-weight:700; font-size:11px; }
    .code-box { background:#02060d; border:1px dashed #00d4ff; padding:16px; border-radius:6px; text-align:center; margin:20px 0; font-family:monospace; font-size:24px; letter-spacing:4px; color:#00d4ff; font-weight:800; }
    .btn { display:inline-block; background:linear-gradient(135deg,#00f090,#00a8ff); color:#020812 !important; text-decoration:none; padding:12px 28px; border-radius:6px; font-weight:800; font-size:13px; text-transform:uppercase; margin:15px 0; box-shadow:0 4px 15px rgba(0,240,144,0.3); }
    .info-card { background:rgba(2,8,18,0.7); border:1px solid rgba(0,240,144,0.25); border-radius:8px; padding:16px 20px; margin:20px 0; }
    .footer { background:#02060d; padding:22px; text-align:center; font-size:11.5px; color:#64748b; border-top:1px solid rgba(255,255,255,0.08); }
    .footer a { color:#00d4ff; text-decoration:none; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>THE SMART MAG QUANT NETWORK</h1>
      <div style="font-size:11.5px; color:#00d4ff; margin-top:5px; font-weight:600; letter-spacing:0.5px;">Institutional Multi-Exchange Trading Engine</div>
    </div>
    <div class="content">
      ''' + content_html + '''
    </div>
    <div class="footer">
      <p style="margin:4px 0;">&copy; 2026 TheSmartMag Quant Network &bull; <a href="https://trade.thesmartmag.com">trade.thesmartmag.com</a></p>
      <p style="margin:4px 0;">Desk Inquiries: <a href="mailto:support@thesmartmag.com">support@thesmartmag.com</a> &bull; <a href="mailto:contact@thesmartmag.com">contact@thesmartmag.com</a> &bull; <a href="mailto:query@thesmartmag.com">query@thesmartmag.com</a></p>
      <p style="font-size:10px; color:#475569; margin-top:8px;">This is an automated encrypted dispatch. If you did not initiate this action, please secure your account immediately.</p>
    </div>
  </div>
</body>
</html>'''

def send_welcome_email(to_email, name, role='trader', phone='', country='US', preferred_exchange='both'):
    subject = 'Welcome to TheSmartMag Quant Network - Trader Access Granted'
    ex_display = 'CoinSwitch Pro & Delta Exchange India (Dual Engine)'
    if preferred_exchange == 'delta':
        ex_display = 'Delta Exchange India (F&O)'
    elif preferred_exchange == 'coinswitch':
        ex_display = 'CoinSwitch Pro (Spot)'
    phone_html = '<div>&bull; <strong>Registered Mobile:</strong> ' + str(phone) + '</div>' if phone else ''
    content = '<p>Greetings <strong>' + str(name) + '</strong>,</p>' + \
      '<p>Your trader account on <strong>TheSmartMag Quant Network</strong> has been successfully created and verified.</p>' + \
      '<div class="info-card">' + \
      '<div style="margin-bottom:10px; font-size:12px; color:#00f090; font-weight:800; letter-spacing:1px; text-transform:uppercase;">Account Credentials &amp; Profile:</div>' + \
      '<div>&bull; <strong>Trader Email:</strong> <span style="color:#00d4ff;">' + str(to_email) + '</span></div>' + \
      '<div>&bull; <strong>Assigned Role:</strong> <span class="badge">' + str(role).upper() + '</span></div>' + \
      '<div>&bull; <strong>Preferred Broker:</strong> ' + str(ex_display) + '</div>' + \
      '<div>&bull; <strong>Region / Country:</strong> ' + str(country) + '</div>' + \
      phone_html + '</div>' + \
      '<p>You can now log in to your personal terminal to access live TradingView charts, execute manual multi-broker orders, connect your API keys, and track your private portfolio positions.</p>' + \
      '<div style="text-align:center; margin:25px 0;"><a href="https://trade.thesmartmag.com/" class="btn">Enter Trading Terminal</a></div>' + \
      '<p style="font-size:12.5px; color:#94a3b8;">Need technical assistance or broker connectivity setup? Reach out to our dedicated support desk at <a href="mailto:support@thesmartmag.com" style="color:#00d4ff;">support@thesmartmag.com</a> or <a href="mailto:query@thesmartmag.com" style="color:#00d4ff;">query@thesmartmag.com</a>.</p>'
    html = get_base_html_template('Welcome to TheSmartMag Quant Network', content, SUPPORT_EMAIL)
    return _send_email(SUPPORT_EMAIL, to_email, subject, html)

def send_login_alert_email(to_email, name, ip, user_agent, timestamp, location=''):
    subject = 'Security Alert: New Sign-in to TheSmartMag Quant Account'
    loc_html = ('<div>&bull; <strong>Approximate Location:</strong> ' + str(location) + '</div>') if location else ''
    content = '<p>Hello <strong>' + str(name or 'Trader') + '</strong>,</p>' + \
      '<p>A successful sign-in to your <strong>TheSmartMag Quant Network</strong> account was recently detected.</p>' + \
      '<div class="info-card" style="border-color:rgba(0,212,255,0.3);">' + \
      '<div style="margin-bottom:10px; font-size:12px; color:#00d4ff; font-weight:800; letter-spacing:1px; text-transform:uppercase;">Sign-in Telemetry Details:</div>' + \
      '<div>&bull; <strong>Account Email:</strong> <span style="color:#00d4ff;">' + str(to_email) + '</span></div>' + \
      '<div>&bull; <strong>Timestamp:</strong> ' + str(timestamp) + '</div>' + \
      '<div>&bull; <strong>IP Address:</strong> <span style="font-family:monospace; color:#00f090;">' + str(ip) + '</span></div>' + \
      loc_html + \
      '<div>&bull; <strong>Device / Browser:</strong> <span style="font-size:12.5px; color:#cbd5e1;">' + str(user_agent) + '</span></div>' + \
      '<div>&bull; <strong>Security Status:</strong> <span class="badge">AUTHORIZED SESSION</span></div>' + \
      '</div>' + \
      '<p style="font-size:13px; color:#cbd5e1;">If this was you, no action is required. If you did not recognize this activity, please reset your password immediately and contact our security desk at <a href="mailto:support@thesmartmag.com" style="color:#00d4ff;">support@thesmartmag.com</a>.</p>' + \
      '<div style="text-align:center; margin:22px 0;"><a href="https://trade.thesmartmag.com/" class="btn">Open Trader Cockpit</a></div>'
    html = get_base_html_template('Security Login Alert', content, SUPPORT_EMAIL)
    return _send_email(SUPPORT_EMAIL, to_email, subject, html)

def send_password_reset_email(to_email, name, otp_code, reset_token):
    subject = 'Password Reset Request - TheSmartMag Quant Network'
    reset_url = 'https://trade.thesmartmag.com/?reset_token=' + str(reset_token) + '&email=' + str(to_email)
    content = '<p>Greetings <strong>' + str(name or 'Trader') + '</strong>,</p>' + \
      '<p>We received a request to reset the password for your trader account associated with <strong>' + str(to_email) + '</strong>.</p>' + \
      '<p>Use the 6-digit verification code below to complete your password reset:</p>' + \
      '<div class="code-box">' + str(otp_code) + '</div>' + \
      '<p style="font-size:13px;">This verification code is valid for <strong>15 minutes</strong>. You can also reset your password directly using the secure link below:</p>' + \
      '<div style="text-align:center; margin:20px 0;"><a href="' + reset_url + '" class="btn">Reset My Password</a></div>' + \
      '<p style="font-size:12px; color:#94a3b8;">If you did not initiate this request, you can safely ignore this email. Your current password remains secure.</p>' + \
      '<p style="font-size:12px; color:#94a3b8;">For security questions, contact <a href="mailto:support@thesmartmag.com" style="color:#00d4ff;">support@thesmartmag.com</a> or <a href="mailto:query@thesmartmag.com" style="color:#00d4ff;">query@thesmartmag.com</a>.</p>'
    html = get_base_html_template('Password Reset Request', content, SUPPORT_EMAIL)
    return _send_email(SUPPORT_EMAIL, to_email, subject, html)

def send_inquiry_confirmation(to_email, name, subject_topic, sender_type='query'):
    sender_addr = QUERY_EMAIL if sender_type == 'query' else CONTACT_EMAIL
    subject = 'Receipt: ' + str(subject_topic) + ' - TheSmartMag Quant Network'
    content = '<p>Hello <strong>' + str(name) + '</strong>,</p>' + \
      '<p>Thank you for contacting TheSmartMag Quant Network. We have received your submission regarding <strong>' + str(subject_topic) + '</strong>.</p>' + \
      '<p>Our quantitative engineering and support team will review your inquiry and follow up within 24 business hours.</p>' + \
      '<div class="info-card" style="border-color:rgba(0,212,255,0.3);">' + \
      '<div><strong>Assigned Desk:</strong> ' + str(sender_addr) + '</div>' + \
      '<div><strong>Status:</strong> Active Ticket In Queue</div>' + \
      '</div>' + \
      '<p style="font-size:12.5px; color:#94a3b8;">For immediate trading questions, visit <a href="https://trade.thesmartmag.com" style="color:#00d4ff;">trade.thesmartmag.com</a> or email <a href="mailto:contact@thesmartmag.com" style="color:#00d4ff;">contact@thesmartmag.com</a>.</p>'
    html = get_base_html_template(subject, content, sender_addr)
    return _send_email(sender_addr, to_email, subject, html)

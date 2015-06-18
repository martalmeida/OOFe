import smtplib
from email.mime.text import MIMEText as emailtext


def send(toaddr,msg,addSubject=''):
  username='ocean.forec.engine@gmail.com'
  password='GreatTool'

  fromaddr=username

  server = smtplib.SMTP('smtp.gmail.com:587')
  server.starttls()
  server.login(username,password)

  m = emailtext(msg)
  if addSubject: m['Subject'] = 'OOFe update - '+addSubject
  else: m['Subject'] = 'OOFe update'
  m['From'] = fromaddr
  m['To'] = ','.join(toaddr)


  server.sendmail(fromaddr, toaddr, m.as_string())
  server.quit()

if __name__=='__main__':
  import sys
  dest=sys.argv[1].split(',')
  msg=sys.argv[2]
  send(dest,msg)

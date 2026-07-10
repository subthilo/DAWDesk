import paramiko

host = '192.168.1.139'
user = 'pi'
password = 'IwiKWuh2K'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=user, password=password)

stdin, stdout, stderr = client.exec_command('journalctl -u dawdesk.service -n 50 --no-pager')
print("STDOUT:", stdout.read().decode())
print("STDERR:", stderr.read().decode())
client.close()

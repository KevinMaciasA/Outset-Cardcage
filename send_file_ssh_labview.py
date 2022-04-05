import os, socket, time, sys, subprocess, datetime, threading, time
import SimpleHTTPServer, SocketServer
import paramiko
import getpass


# Connecting/auth:
MY_IP_ADDR = "10.134.246.249"
DEFAULT_MI_BOARD_ADDRESS = "10.134.246.251"
TEMP_HTTP_PORT = 8000

# Fast timeout for short commands, do not use for lengthy processes.
DEFAULT_TIMEOUT = 5

# Board address we're using for this run: might be overridden
# by command-line argument, might just be DEFAULT_MI_BOARD_ADDRESS.
MI_ADDRESS = None
httpd = None

def read_til_text(s, match_text="---", timeout=DEFAULT_TIMEOUT):
    response = ""
    s.settimeout(timeout)

    while True:
        try:
            chunk = s.recv(1)
        except socket.timeout as e:
            break

        if chunk == '':
            print('Unexpected socket read failure, this is bad')
            os._exit(1)

        response = response + chunk

        # Rapid break out if we found what we're looking for:
        if match_text and response.find(match_text) > -1:
            return response

    if match_text and response.find(match_text) == -1:
        print(response)
        print('*** Exception: expected to find response "%s" in previous message' % match_text)
        os._exit(1)

    return response

def connect_to_mi_board():

    global MI_ADDRESS

    MI_ADDRESS = DEFAULT_MI_BOARD_ADDRESS
    print('Connecting to MI board at %s...' % MI_ADDRESS)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    MIPASSWORD = "Hotel2planet!*#)"
    ssh.connect(MI_ADDRESS, username='root', password=MIPASSWORD) #Added By MP
    channel = ssh.get_transport().open_session()
    channel.exec_command("sh")

    return (ssh, channel)

def send_file():
    global httpd
	
    ssh, channel = connect_to_mi_board()
    print('Switching to destination dir...')
    channel.send('cd %s \necho ---\n' % sys.argv[1][: sys.argv[1].rfind('/') + 1])
    response = read_til_text(channel, timeout=3)
    
    print('Starting the web server...')
    # Fire up our thread and let it settle...
    thread = threading.Thread(target=web_server_thread)
    thread.start()
    time.sleep(1)
	
    # Now tell the board to pull the file.
    get_command = 'wget -O %s http://%s:%d/%s ' % (sys.argv[1],MY_IP_ADDR, TEMP_HTTP_PORT,sys.argv[2])
    print ('%s' % get_command)
    channel.send('%s\necho ---\n' % get_command)
    response = read_til_text(channel, timeout=30)
	
    print('Sanity checking...')
    channel.send("ls\necho ---\n\n")
    response = read_til_text(channel, timeout=5)
    if '%s' % sys.argv[2] in response:
        print('-------')
        print('File Sent successfully')
        print('-------')
        print('CLOSE WINDOW & PERFORM SUGGESTED INSTRUCTIONS')
        httpd.shutdown()
        httpd.socket.close()
        channel.close()
        ssh.close()
        return

    print('File Transfer failed')
    httpd.shutdown()
    httpd.socket.close()
    
    channel.close()
    ssh.close()
    os._exit(0)



# Only handle the one request, that's all we need.
def web_server_thread():
    global httpd 

    Handler = SimpleHTTPServer.SimpleHTTPRequestHandler
    httpd = SocketServer.TCPServer(("", TEMP_HTTP_PORT), Handler)
    httpd.handle_request()
    httpd.shutdown()
    httpd.socket.close()


if __name__ == '__main__':
    send_file()


import socket
import time

addr = "192.168.1.12"
port = 1112

sock = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )

for i in range(110):
	sock.sendto(str(i), (addr, port))
	print i
	time.sleep(0.025)
#/usr/bin/env python

import re
import json
import time
import socket
import urllib2
import os
from subprocess import Popen, PIPE

class r2pipeException(Exception):
	pass

def version():
	return "0.2"

class open:
	def __init__(self, filename, writeable=False, bininfo=True):
		try:
			self.pipe = [ int(os.environ['R2PIPE_IN']), int(os.environ['R2PIPE_OUT']) ]
			self._cmd = self._cmd_pipe
			self.url = "#!pipe"
			return
		except:
			pass
		if filename.startswith("#!pipe"):
			print "ERROR: Cannot use #!pipe without R2PIPE_{IN|OUT} env"
			return
		if filename.startswith("http"):
			self._cmd = self._cmd_http
			self.uri = filename + "/cmd"
		elif filename.startswith("tcp"):
			r = re.match(r'tcp://(\d+\.\d+.\d+.\d+):(\d+)/?', filename)
			if not r:
				raise r2pipeException("String doesn't match tcp format")
			self._cmd = self._cmd_tcp
			self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self.conn.connect((r.group(1), int(r.group(2))))
		else:
			self._cmd = self._cmd_process
			cmd = ["r2", "-q0", filename]
			if writeable:
				cmd = cmd[:1] + ["-w"] + cmd[1:]
			if not bininfo:
				cmd = cmd[:1] + ["-n"] + cmd[1:]
			self.process = Popen(cmd, shell=False, stdin=PIPE, stdout=PIPE)
			self.process.stdout.read(1) # Reads initial \x00

	def _cmd_process(self, cmd):
		self.process.stdin.write(cmd)
		self.process.stdin.write('\n')
		self.process.stdin.flush()
		out = ""
		while True:
			out += self.process.stdout.read(1) # 1? ORLY?
			if len(out)<1:
				return None
			if out[-1] == '\x00':
				break
		return out[:-1]

	def _cmd_tcp(self, cmd):
		res = ""
		self.conn.sendall(cmd)
		data = self.conn.recv(512)
		while data:
			res += data
			data = self.conn.recv(512)
		return res

	def _cmd_pipe(self, cmd):
		res = ""
		os.write (self.pipe[1], cmd)
		data = os.read (self.pipe[0], 1024)
		return data
		while data:
			res += data
			data = os.read (self.pipe[0], 1024)
		return res

	def _cmd_http(self, cmd):
		try:
			response = urllib2.urlopen('{uri}/{cmd}'.format(uri=self.uri, cmd=cmd))
			return response.read()
		except urllib2.URLError:
			pass
		return None

	def cmd(self, cmd):
		return self._cmd(cmd)

	def cmdj(self, cmd):
		return self.cmd_json(cmd)

	def cmd_json(self, cmd):
		try:
			data = json.loads(self.cmd(cmd))
		except (ValueError, KeyError, TypeError) as e:
			print ("r2pipe.cmd_json.Error",e)
			data = None
		return data

# Hello World
if __name__ == "__main__":
	print "[+] Spawning r2 tcp and http servers"
	system ("pkill r2")
	system ("r2 -qc.:9080 /bin/ls &")
	system ("r2 -qc=h /bin/ls &")
	time.sleep(1)
	# Test r2pipe with local process
	print "[+] Testing python r2pipe local"
	rlocal = open("/bin/ls")
	print rlocal.cmd("pi 5")
	#print rlocal.cmd("pn")
	info = rlocal.cmd_json("ij")
	print ("Architecture: " + info['bin']['machine'])

	# Test r2pipe with remote tcp process (launch it with "r2 -qc.:9080 myfile")
	print "[+] Testing python r2pipe tcp://"
	rremote = open("tcp://127.0.0.1:9080")
	disas = rremote.cmd("pi 5")
	if not disas:
		print "Error with remote tcp conection"
	else:
		print disas

	# Test r2pipe with remote http process (launch it with "r2 -qc=H myfile")
	print "[+] Testing python r2pipe http://"
	rremote = open("http://127.0.0.1:9090")
	disas = rremote.cmd("pi 5")
	if not disas:
		print "Error with remote http conection"
	else:
		print disas
	system ("pkill -INT r2")

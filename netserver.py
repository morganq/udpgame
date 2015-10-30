from player import Player
from vector2 import Vector2
from netshared import *
from dodgeballscene import *

import random
import socket
import time

try:
	import win32com
	import win32com.client
except:
	pass

class ClientInfo:
	def __init__(self, cid, addr, port, entity):
		self.cid = cid
		self.addr = addr
		self.port = port
		self.name = "player"
		self.entity = entity
		self.latency = 0
		self.pingTimestamp = 0
		self.admin = False
		self.super = []
		self.exThrow = []
		self.chargeStartTime = 0


class NetServer(NetCommon):
	def __init__(self, listenPort=DEFAULT_SERVER_LISTEN_PORT):
		NetCommon.__init__(self, listenPort)
		self.clients = []

		self.stateUpdateTimer = 0

		self.netidcounter = 0
		self.allentities = []
		self.ended = False

		self.score = [0,0]

		self.periodic.add(self.sendStateUpdate, TICKTIME)
		self.periodic.add(self.sendServerVars, 5.0)

	def sendToClient(self, client, data):
		self.sendPacket(data, client.addr, client.port)

	def sendEnsuredToClient(self, client, data):
		self.sendEnsuredPacket(data, client.addr, client.port)		

	def update(self, game, dt):
		NetCommon.update(self, game, dt)

		if game.started:
			if self.ended:
				self.nextRoundTimer -= dt
				if self.nextRoundTimer <= 0:
					self.startRound(game)
			else:
				#Check for victory condition
				teams = [0, 0]
				if len(self.clients) > 1:
					for c in self.clients:
						if c.entity.health > 0:
							teams[c.entity.team] += 1
					if teams[0] == 0:
						self.endRound(1)
					elif teams[1] == 0:
						self.endRound(0)
					game.score = self.score

	def endRound(self, winner):
		self.score[winner] += 1
		self.broadcast({"type":"endround", "winner": winner, "score":self.score})
		self.ended = True
		self.nextRoundTimer = 5.0

	def sendStateUpdate(self):
		game = self.game
		if not game.started:
			return
		data = {"type":"state", "time":self.t, "entities":[], "players":[]}
		for e in game.scene.sceneEntities:
			if hasattr(e, "netid"):
				entity_data = self.getEntityStateData(e)
				if entity_data:
					data["entities"].append( entity_data )
		#for c in self.clients:
		#	data["players"].append( self.getPlayerStateData(c.entity) )
		self.broadcast(data)

	def getPlayerStateData(self, p):
		data = self.getEntityStateData(p)
		return data

	def getEntityStateData(self, e):
		data = {}
		data["netid"] = e.netid
		data["position"] = e.position
		data["velocity"] = e.velocity		
		return data

	def broadcast(self, data):
		for c in self.clients:
			self.sendPacket(data, c.addr, c.port)

	def ensuredBroadcast(self, data):
		for c in self.clients:
			self.sendEnsuredPacket(data, c.addr, c.port)		

	def spawn(self, ent, name, extra = {}, owner=None, ensured=True):
		ent.netid = self.netidcounter
		self.allentities.append(ent)
		self.netidcounter += 1
		if owner:
			owner = owner.cid
		data = {
			"type":"spawn",
			"time":self.t,
			"name":name,
			"owner":owner,
			"position":ent.position.asTuple(),
			"velocity":ent.velocity.asTuple(),
			"netid":ent.netid,
			"args" : []}
		for k, v in extra.items():
			data[k] = v
		if ensured:
			self.ensuredBroadcast(data)
		else:
			self.broadcast(data)

	def startRound(self, game):
		self.ensuredBroadcast({"type":"start"})
		self.ended = False
		game.started = True
		game.setScene(DodgeballScene())
		i = 0
		for c in self.clients:
			p = c.entity
			# figure out which team each player is on and how to position them.
			p.team = i % 2
			if p.team == 0:
				p.position.x = 80 - int(i/2) * 7
			else:
				p.position.x = 240 + int(i/2) * 7
			p.position.y = int(i / 2) * 36 + 40
			i += 1
			game.scene.add(p)
			p.initialize()
			self.spawn(p, "player", {"owner":c.cid, "args":[p.team]})

	def getClient(self, info):
		for c in self.clients:
			if info == (c.addr, c.port):
				return c
				
	def sendSoundMessage(self, name):
		self.broadcast({"type":"sound", "name":name})

	def sendServerVars(self):
		if not len(self.clients):
			return
		maxlat = max(c.latency for c in self.clients)
		interp = TICKTIME + maxlat * 1
		self.broadcast({"type":"serverVars", "interp":interp})

	def destroyNetEntity(self, entity):
		self.broadcast({"type":"destroy", "netid":entity.netid})
		self.game.scene.sceneEntities.remove(entity)

	def sendPlayerHit(self, player):
		player.hitTimer = 0.5
		self.broadcast({"type":"playerHit", "time":self.t, "netid":player.netid, "hitTimer":player.hitTimer})

	def sendAnimation(self, spr):
		print "send anim: ", spr.currentAnimation.name
		self.broadcast({"type":"animation", "time":self.t, "name":spr.currentAnimation.name, "netid":spr.netid})

	def process_pregame_hello(self, data, game, info):
		self.ensuredBroadcast({"type":"numplayers","value":len(self.clients)})
		print(info[0] + " joined the game.")
		game.scene.playersInGame += 1

	def process_ingame_hello(self, data, game, info, player, client):
		self.startRound(game)

	def process_hello(self, data, game, info):
		for c in self.clients:
			if c.addr == info[0] and c.port == info[1]:
				print("Client can't connect a second time.")
				return

		player = Player(Vector2(0,0))
		c = ClientInfo(len(self.clients), info[0], info[1], player)
		if len(self.clients) == 0:
			c.admin = True
		self.clients.append(c)
		self.sendEnsuredToClient(c, {"type": "id", "clientId": c.cid, "admin":c.admin} )

		if not game.started:
			self.process_pregame_hello(data, game, info)

		else:
			self.process_ingame_hello(data, game, info, player, c)

	def process_timeSyncRequest(self, data, game, info):
		c = self.getClient(info)
		if c is None:
			return
		self.sendToClient(c, {"type":"timeSyncResponse", "client":data["client"], "server":self.t})

	def process_start(self, data, game, info):
		c = self.getClient(info)
		if c is None or not c.admin:
			return
		self.startRound(game)

	def process_playerInput(self, data, game, info):
		c = self.getClient(info)
		if c is None:
			return
		p = c.entity
		vel,_ = p.getVelocityAndAnim(data["xd"], data["yd"])
		targetpos = Vector2(*data["position"]) + vel * game.dt
		offset = targetpos - p.position
		if offset.lengthSquared() > 4*4:
			direction = offset.normalized()
			p.xDirection = round(round(direction.x * 2) / 2)
			p.yDirection = round(round(direction.y * 2) / 2)
		else:
			p.xDirection = 0
			p.yDirection = 0

	def process_fire(self, data, game, info):
		c = self.getClient(info)
		if c is None:
			return
		proj = Projectile(c.entity.position)
		proj.owner = c.entity
		speed = 100 + min(self.t - c.chargeStartTime,1) * 100
		proj.velocity = Vector2(*data["direction"]).normalized() * speed
		game.scene.add(proj)
		self.spawn(proj, "projectile", owner=c, ensured=False)
		c.entity.play("throw")
		c.entity.charge = 0

	def process_charge(self, data, game, info):
		c = self.getClient(info)
		if c is None:
			return
		c.entity.charge = 1.0
		c.chargeStartTime = self.t


	def process_playerInfo(self, data, game, info):
		c = self.getClient(info)
		if c is None:
			return
		c.name = data["name"]
		print(c.addr + " identified as " + c.name)

	def process_chat(self, data, game, info):
		c = self.getClient(info)
		c.entity.chatText = data["text"]
		c.entity.chatTimer = 5
		if chat:
			self.broadcast({"type":"chat", "text":data["text"], "netid":c.entity.netinfo["netid"]})

	def process_ping(self, data, game, info):
		c = self.getClient(info)
		if c is None:
			return
		key = "client_" + str(c.cid) + "_latency"
		diff = self.t - data["time"]
		if diff > 1.0 or diff < 0:
			return
		self.averagedData.add(self.t, key, diff)
		c.latency = self.averagedData.get_max(self.t, key, 10)
		self.sendToClient(c, {"type":"pong"})
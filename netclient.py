from netshared import *
from dodgeballscene import *
from player import PlayerController
import content
import math

TIMESYNCS = 5
INTERP = TICKTIME + 0.15

class NetClient(NetCommon):
	def __init__(self, listenPort = DEFAULT_CLIENT_LISTEN_PORT):
		NetCommon.__init__(self, listenPort)
		self.sendAddr = None
		self.sendPort = None

		self.clientId = None
		self.timeSinceUpdate = 0

		self.latency = 0
		self.pingTimestamp = 0
		
		self.myPlayer = None

		self.stun_t = 0
		self.serverTime = 0
		self.serverTimeOffsetFromClientTime = 0
		self.timeSyncResponses = []

		self.periodic.add(self.sendPing, 1.0)
		self.periodic.add(self.sendTimeSyncRequest, 0.25)
		self.periodic.add(self.sendInputs, 0.05)

		self.lastStateUpdate = 0

		self.interp = INTERP

	def lookupEntity(self, scene, netid):
		for e in scene.sceneEntities:
			if hasattr(e, "netid") and e.netid == netid:
				return e

	def update(self, game, dt):
		NetCommon.update(self, game, dt)
		self.serverTime = self.t + self.serverTimeOffsetFromClientTime

		self.timeSinceUpdate += dt

		if self.myPlayer and self.serverTime - self.interp >= self.lastStateUpdate:
			self.interp += dt / 4.0
			print "interp upgrade:", self.interp

		self.updateNetEntities(game, dt)

	def updateNetEntities(self, game, dt):
		for e in game.scene.sceneEntities:
			if hasattr(e, "netid") and e.netid >= 0 and not e.predict:
				if e == self.myPlayer:
					continue
				e.serverTime = self.serverTime
				st = e.getOldState(e.serverStates, self.serverTime - self.interp)
				e.position = st["position"]
				e.velocity = st["velocity"]


	def connect(self, addr, port = DEFAULT_SERVER_LISTEN_PORT):
		self.sendAddr = addr
		self.sendPort = port
		self.sendEnsuredToServer( {"type":"hello"} )
		print("Connecting...")

	def sendToServer(self, data):
		self.sendPacket(data, self.sendAddr, self.sendPort)

	def sendEnsuredToServer(self, data):
		self.sendEnsuredPacket(data, self.sendAddr, self.sendPort)		

	def sendPing(self):
		self.pingTimestamp = self.t
		self.sendToServer({"type":"ping", "time":self.serverTime})

	def updateEntity(self, time, entity, edata, game):
		state = edata
		state["t"] = time
		entity.serverStates.append(state)

	def updatePlayer(self, time, entity, edata, game):
		self.updateEntity(time, entity, edata, game)

	def sendInputs(self):
		if not self.myPlayer:
			return
		self.sendToServer({
			"type":"playerInput",
			"time":self.serverTime,
			"xd" : self.myPlayer.xDirection, "yd" : self.myPlayer.yDirection,
			"position": self.myPlayer.position.asTuple()})

	def sendFireMessage(self):
		self.sendToServer({
			"type":"fire",
			"time":self.serverTime
			})
		
	def sendPlayerInfo(self, name):
		self.sendEnsuredToServer({"type":"playerInfo", "name":name})

	def sendTimeSyncRequest(self):
		if len(self.timeSyncResponses) < TIMESYNCS:
			self.sendToServer({"type":"timeSyncRequest", "client":self.t})

	def process_timeSyncResponse(self, data, game, info):
		orig = data["client"]
		now = self.t
		lat = (now - orig)
		self.serverTimeOffsetFromClientTime = (data["server"] - data["client"]) - lat / 2
		self.timeSyncResponses.append(self.serverTimeOffsetFromClientTime)
		if len(self.timeSyncResponses) >= TIMESYNCS:
			self.timeSyncResponses.sort()
			self.serverTimeOffsetFromClientTime = self.timeSyncResponses[2]
			self.serverTime = self.t + self.serverTimeOffsetFromClientTime

	def process_start(self, data, game, info):
		game.setScene(DodgeballScene())
		game.started = True
		game.pauseInput = False
		
	def process_numplayers(self, data, game, info):
		game.scene.playersInGame = data["value"]

	def process_spawn(self, data, game, info):
		entName = data["name"]
		ctor = self.netEntities[entName]
		ent = ctor(Vector2(*data["position"]), *data["args"])
		ent.velocity = Vector2(*data["velocity"])
		ent.position += ent.velocity * (self.serverTime - data["time"])
		ent.netid = data["netid"]
		game.scene.add(ent)

		if data["name"] == "projectile":
			if data["owner"] == self.clientId:
				ent.owner = self.myPlayer
				self.myPlayer.throwingWaitForServer = False

		if data["name"] == "player":
			if data["owner"] == self.clientId:
				controller = PlayerController(ent, self)
				self.myPlayer = ent
				game.controller = controller
			ent.initialize()

	def process_destroy(self, data, game, info):
		ent = self.lookupEntity(game.scene, data["netid"])
		if ent:
			game.scene.sceneEntities.remove(ent)

	def process_id(self, data, game, info):
		self.clientId = data["clientId"]
		if data["admin"]:
			game.admin = True
		print("Connected.")

	def process_state(self, data, game, info):
		self.lastStateUpdate = data["time"]
		self.simulatedRandomLatency = self.simulatedRandomLatencyVal
		self.timeSinceUpdate = 0
		for edata in data["entities"]:
			entity = self.lookupEntity(game.scene, edata["netid"])
			if entity:
				self.updateEntity(data["time"], entity, edata, game)
		for pdata in data["players"]:
			player = self.lookupEntity(game.scene, pdata["netid"])
			if player:
				self.updatePlayer(data["time"], player, pdata, game)

	def process_chat(self, data, game, info):
		p = self.lookupEntity(game.scene, data["netid"])
		if p is not None:
			p.chatText = data["text"]
			p.chatTimer = 5
		
	def process_animation(self, data, game, info):
		p = self.lookupEntity(game.scene, data["netid"])
		if p is not None and p is not self.myPlayer:
			p.play(data["name"])

	def process_endround(self, data, game, info):
		game.score = data["score"]
		if data["winner"] == self.myPlayer.team:
			game.scene.victoryMessage = "Victory!"
			content.sounds["victory.wav"].play()
		else:
			game.scene.victoryMessage = "Defeat."
			content.sounds["defeat.wav"].play()
			
	def process_sound(self, data, game, info):
		content.sounds[data["name"]].play()

	def process_pong(self, data, game, info):
		self.averagedData.add(self.t, "latency", self.t - self.pingTimestamp)
		self.latency = self.averagedData.get_avg(self.t, "latency", 10)

	def process_serverVars(self, data, game, info):
		self.interp = data["interp"]
		print "INTERP: ", self.interp

	def process_playerHit(self, data, game, info):
		p = self.lookupEntity(game.scene, data["netid"])
		if p is not None:
			p.play("hit", True)
			if p == self.myPlayer:
				p.hitTimer = data["hitTimer"]
			else:
				p.hitTimer = data["hitTimer"] + self.interp

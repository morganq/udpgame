#Base class for basically everything in the game.

class Entity:
	def __init__(self):
		self.name = "entity"
		
	def update(self, dt):
		pass

	def draw(self, screen):
		pass



class NetEntity(Entity):
	def __init__(self):
		Entity.__init__(self)
		self.clientStates = []
		self.serverStates = []
		self.netid = -1
		self.serverTime = 0
		self.predict = False
		self.interpVals = []
		self.lastStateUpdate = 0

	def update(self, dt):
		st = self.recordState()
		self.clientStates.append(st)
		self.clientStates = self.clientStates[-40:]
		self.serverStates = self.serverStates[-40:]
		self.interpVals = self.interpVals[-40:]
		#self.clientStates.sort(lambda a,b:cmp(a["t"], b["t"]))
		#self.serverStates.sort(lambda a,b:cmp(a["t"], b["t"]))

	def recordState(self):
		st = {
			"t" : self.serverTime
		}
		return st

	def getOldState(self, states, t):
		next = None
		prev = None
		if len(states) < 2:
			return self.recordState()
		i = len(states) - 2
		while i >= 1:
			prev = states[i]
			if prev["t"] < t:
				break
			i -= 1
		prev = states[i]
		next = states[i+1]

		tt = next["t"] - prev["t"]
		mt = t - prev["t"]
		if tt == 0:
			print t, prev, next, states
		mh = mt / tt
		if mh > 1:
			print "EXTRAPOLATING!!"
		self.interpVals.append(mh)
		newState = self.interpolateState(prev, next, mh)
		return newState

	def interpolateState(self, prev, next, mh):
		ml = 1 - mh
		return {"t":next["t"] * mh + prev["t"] * ml}	

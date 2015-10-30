import pygame

class Periodic:
	def __init__(self):
		self.fns = {}
		self.time = 0

	def add(self, fn, every):
		self.fns[fn] = (every, self.time + every)

	def update(self):
		self.time = pygame.time.get_ticks() / 1000.0
		for fn, (every, next) in self.fns.items():
			if self.time > next:
				fn()
				self.fns[fn] = (every, max(next, self.time) + every)

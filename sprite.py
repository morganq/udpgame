import pygame
from entity import NetEntity
from vector2 import Vector2
import content

#An animation is a list of frames, and the necessary state info
#A frame is a (image, rect) pair
class Animation:
	def __init__(self, frames, framerate, looping):
		self.frames = frames
		self.framerate = framerate
		self.looping = looping
		self.t = 0

	def update(self, dt):
		self.t += dt
		
	def getImage(self):
		#Figure out which frame index we're at based on time and framerate
		frameNum = int(self.framerate * self.t)
		if frameNum >= len(self.frames):
			if self.looping:
				frameNum = frameNum % len(self.frames)
			else:
				frameNum = len(self.frames) - 1
		return self.frames[frameNum]

	def isDone(self):
		return self.looping or int(self.framerate * self.t) >= len(self.frames)

class Sprite(NetEntity):
	def __init__(self, position):
		NetEntity.__init__(self)
		#Physics stuff
		self.position = position
		self.velocity = Vector2(0, 0)
		self.acceleration = Vector2(0, 0)

		#Image stuff
		self.animations = {}
		self.currentAnimation = None
		self.flipHorizontal = False
		self.offset = Vector2(0, 0)
		self.visible = True
		
		#layering
		self.layerIndex = 0
		
		#rotation
		self.angle = 0

	def addAnimation(self, name, image, startX, startY, frameWidth, frameHeight, numFrames, framerate, looping = True):
		frames = []
		for i in range(numFrames):
			rect = pygame.Rect(startX + i * frameWidth, startY, frameWidth, frameHeight)
			frame = (image, rect)
			frames.append(frame)
		anim = Animation(frames, framerate, looping)
		self.animations[name] = anim
		self.currentAnimation = anim
		self.currentAnimation.name = name
		
	def play(self, name, force=False):
		if (self.currentAnimation != self.animations[name] and self.currentAnimation.isDone()) or force:
			self.currentAnimation = self.animations[name]
			self.currentAnimation.t = 0

	def addStaticImage(self, image):
		rect = image.get_rect()
		self.addAnimation("default", image, rect[0], rect[1], rect[2], rect[3], 1, 0, False)

	def update(self, dt):
		NetEntity.update(self, dt)
		self.velocity += self.acceleration * dt
		self.position += self.velocity * dt
		if self.currentAnimation:
			self.currentAnimation.update(dt)

	def draw(self, screen):
		if self.visible and self.currentAnimation:
			(src, rect) = self.currentAnimation.getImage()
			image = pygame.Surface((rect[2], rect[3]),pygame.SRCALPHA)
			image.blit(src, (0,0), rect)
			if self.flipHorizontal:
				image = pygame.transform.flip(image, True, False)
			if self.angle != 0:
				image = pygame.transform.rotate(image, int(self.angle/90) * 90)
			screen.blit(image, (self.position - self.offset).asTuple())

	def recordState(self):
		st = NetEntity.recordState(self)
		st["position"] = self.position
		st["velocity"] = self.velocity
		return st

	def interpolateState(self, prev, next, mh):
		ml = 1 - mh
		newState = NetEntity.interpolateState(self, prev, next, mh)
		
		newState["position"] = next["position"] * mh + prev["position"] * ml
		newState["velocity"] = next["velocity"] * mh + prev["velocity"] * ml

		return newState
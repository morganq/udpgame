from sprite import Sprite
from vector2 import Vector2
import pygame
import content
import random
import g

MID = 160

class Player(Sprite):
	def __init__(self, position, team = 0):
		Sprite.__init__(self, position)
		self.addAnimation("stand", content.images['player3.png'],	32 * 0 , 0, 32, 32, 1, 0, True)
		self.addAnimation("runf", content.images['player3.png'],	32 * 1 , 0, 32, 32, 6, 9, True)
		self.addAnimation("runfh", content.images['player3.png'],	32 * 7 , 0, 32, 32, 6, 9, True)
		self.addAnimation("runb", content.images['player3.png'],	32 * 13, 0, 32, 32, 6, 9, True)
		self.addAnimation("runbh", content.images['player3.png'],	32 * 19, 0, 32, 32, 6, 9, True)
		self.addAnimation("catch", content.images['player3.png'],	32 * 25, 0, 32, 32, 1, 0, True)
		self.addAnimation("throw", content.images['player3.png'],	32 * 26, 0, 32, 32, 4, 7, False)
		self.addAnimation("hit", content.images['player3.png'],		32 * 30, 0, 32, 32, 2, 4, True)
		self.addAnimation("jumpf", content.images['player3.png'],	32 * 32, 0, 32, 32, 1, 0, True)
		self.addAnimation("jumpfh", content.images['player3.png'],	32 * 33, 0, 32, 32, 1, 0, True)
		self.addAnimation("jump", content.images['player3.png'],	32 * 34, 0, 32, 32, 1, 0, True)
		self.addAnimation("jumph", content.images['player3.png'],	32 * 35, 0, 32, 32, 1, 0, True)

		self.team = team

		self.name = "player"

		#net
		self.chatMessage = ""
		self.chatTimer = 0
		self.chatFont = pygame.font.Font("visitor1.ttf", 10)

		self.lastAnimation = self.currentAnimation
		
		#particle timer
		self.pTimer = 0

		self.localPlayer = False
		self.localPlayerAnimationName = "stand"
		self.baseSpeed = 80

		self.xDirection = 0
		self.yDirection = 0		

		self.throwingWaitForServer = False
		self.throwTimer = 0

		self.hitTimer = 0

	def initialize(self):
		self.health = 100

		self.play("stand")
		self.offset = Vector2(16, 16)

		self.angle = 0

		self.localPlayer = not g.SERVER and g.game.net.myPlayer == self


	def holdingForward(self):
		return self.xDirection == (1, -1)[self.team]

	def holdingBack(self):
		return self.xDirection == (-1, 1)[self.team]

	def getVelocityAndAnim(self, xd, yd):
		speed = 1.0
		if abs(xd) + abs(yd) > 1:
			speed = 0.7

		animname = None

		vel = Vector2(0,0)

		if xd == -1:
			vel.x = -self.baseSpeed * speed
			if self.team == 0:
				animname = "runb"
			else:
				animname = "runf"
		elif xd == 1:
			vel.x = self.baseSpeed * speed
			if self.team == 0:
				animname = "runf"
			else:
				animname = "runb"
		elif xd == 0:
			vel.x = 0

		if yd == -1:
			vel.y = -self.baseSpeed * speed
			animname = "runf"
		elif yd == 1:
			vel.y = self.baseSpeed * speed
			animname = "runf"
		elif yd == 0:
			vel.y = 0		

		return vel, animname

	def update(self, dt):
		Sprite.update(self, dt)

		if self.chatTimer > 0:
			self.chatTimer -= dt

		if self.team == 0:
			self.flipHorizontal = False
		else:
			self.flipHorizontal = True			

		if self.hitTimer > 0:
			self.hitTimer -= dt
			self.play("hit")
			self.velocity.zero()
			return
		else:
			self.play("stand")
			
		self.velocity, animname = self.getVelocityAndAnim(self.xDirection, self.yDirection)

		self.collideWalls()

		self.throwTimer -= dt
		if self.throwingWaitForServer or self.throwTimer > 0:
			self.velocity.zero()

		self.lastAnimation = self.currentAnimation

	def draw(self, screen):
		Sprite.draw(self, screen)
		x = self.position.x - 7
		y = self.position.y - 20
		w = min(max(self.health, 0) / 100.0 * 14, 13)
		if self.health > 0:
			pygame.draw.rect(screen, (39,65,62), (x-1,y-1, 16, 3), 0)
			pygame.draw.line(screen, (255, 255, 255), (x, y), (x + 13, y))
			pygame.draw.line(screen, (67,102,125), (x, y), (x + w, y))

		if self.chatTimer > 0:
			surf = self.chatFont.render(self.chatText, False, (39, 65, 62))
			if self.flipHorizontal:
				x = x - 4 - surf.get_width()
			else:
				x = x + 18
			screen.blit(surf, (x, y + 2))
			
	def collideWalls(self):
		self.position.y = max(38, self.position.y)
		self.position.y = min(187, self.position.y)
		self.position.x = max(35 - 0.2391 * (self.position.y - 38), self.position.x)
		self.position.x = min(285 + 0.2391 * (self.position.y - 38), self.position.x)

class PlayerController:
	def __init__(self, player, netClient):
		self.player = player
		self.netClient = netClient
		self.lastkx = 0
		self.lastky = 0

	def update(self, dt):
		keys = pygame.key.get_pressed()
		kx = 0
		ky = 0
		if keys[pygame.K_LEFT]:
			kx = -1
		if keys[pygame.K_RIGHT]:
			kx = 1
		if keys[pygame.K_UP]:
			ky = -1
		if keys[pygame.K_DOWN]:
			ky = 1
		if kx != self.lastkx or ky != self.lastky:
			pass

		self.player.xDirection = kx
		self.player.yDirection = ky

		self.lastkx = kx
		self.lastky = ky

	def getEvent(self, evt):
		if evt.type == pygame.KEYDOWN:
			if evt.key == pygame.K_z:
				self.netClient.sendFireMessage()
				self.player.throwingWaitForServer = True
				self.player.throwTimer = 0.5
				self.player.play("throw")


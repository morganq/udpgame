from sprite import *
import g

class Projectile(Sprite):
	def __init__(self, position):
		Sprite.__init__(self, position)
		self.addAnimation("default", content.images['ball.png'], 0 , 0, 15, 15, 1, 0, True)
		self.play("default")
		self.predict = True
		self.owner = None
		self.offset=Vector2(7,7)

	def update(self, dt):
		Sprite.update(self, dt)
		if g.SERVER:
			for e in g.game.scene.sceneEntities:
				if (e.position - self.position).lengthSquared() < 16*16:
					if e.name == "player" and e != self.owner:
						g.game.net.sendPlayerHit(e)
						g.game.net.destroyNetEntity(self)
					break
import dungeonGenerator
from scene import *
from console import set_font
from random import choice, randint, randrange, seed
from math import atan2, ceil, cos, floor, radians, sin

from time import time
import decimal


# Version 0.2 build 3

EMPTY = 0
FLOOR = 1
CORRIDOR = 2
DOOR = 3
DEADEND = 4
WALL = 5
OBSTACLE = 6
CAVE = 7

# Room Types (Negative numbers mean rooms don't have enemies)

START = -1
END = -2

SKULL = 1
SLIME = 2

def round(num):
	return int(decimal.Decimal(num).quantize(decimal.Decimal('1'), rounding=decimal.ROUND_HALF_UP))
	
class DungeonGame (Scene):

	def setup(self):
	
		self.loaded = False
		self.mapSize = 40 # Small: 35, Medium: 55, Large: 70
		self.generateMap(2)
		
		self.loadGraphics()
		self.loadControls()
		
		self.entities = []
		self.generateRooms()
		self.spawnPlayer()
		
		self.printMap()
		
		self.state = 'Play'
		self.loaded = True
		
	def generateMap(self, s=-1):
		if s > 0:
			seed(s)
		self.d = dungeonGenerator.dungeonGenerator(self.mapSize, self.mapSize)
		self.d.placeRandomRooms(5, 11, 2, 2, attempts=15000)
		self.d.generateCorridors('f')
		self.d.connectAllRooms(30)
		# self.d.pruneDeadends(50)
		self.d.findDeadends()
		while self.d.deadends:
			self.d.pruneDeadends(1)
		self.d.placeWalls()
		
		self.map = self.d.grid
		self.rooms = self.d.rooms
		
	def generateRooms(self):
		for r in self.rooms:
			r.rect = Rect(r.x, r.y, r.width, r.height)
			r.type = choice([SKULL, SLIME])
		self.rooms[0].type = START
		self.rooms[-1].type = END
		for r in self.rooms:
			if r.type > 0:
				for i in range(randint(2, 4)):
					self.entities.append(self.getEntityForRoom(r, randrange(r.x, r.x + r.width), randrange(r.y, r.y + r.height)))
					
	def getEntityForRoom(self, room, x, y):
		if room.type == SKULL:
			return Skull(x, y, room)
		elif room.type == SLIME:
			return Slime(x, y, room)
			
	def spawnPlayer(self):
		x = self.rooms[0].x
		y = self.rooms[0].y
		wid = self.rooms[0].width
		hei = self.rooms[0].height
		self.player = Player(x + int(wid / 2), y + int(hei / 2))
		
	def printMap(self):
		'''
		EMPTY = 0
		FLOOR = 1
		CORRIDOR = 2
		DOOR = 3
		DEADEND = 4
		WALL = 5
		OBSTACLE = 6
		CAVE = 7
		'''
		t = ['#', ' ', '•', '=', '~', '%', '*', 'C']
		
		set_font('Menlo', self.size.h * 0.87 / self.mapSize)
		
		# Use the star to represent the player.
		self.map[self.player.x][self.player.y] = 6
		
		s = ''
		for y in range(self.mapSize - 1, -1, -1):
			for x in range(0, self.mapSize):
				s += t[self.map[x][y]]
			s += '\n'
		print(s)
		
		self.map[self.player.x][self.player.y] = 1
		
	def blockAt(self, x, y):
		if x < 0 or y < 0: return EMPTY
		try:
			return self.map[round(x)][round(y)]
		except IndexError:
			return EMPTY
			
	def canWalk(self, x, y):
		return self.player.canWalk(self.blockAt(x, y))
		
	def loadGraphics(self):
		w = self.size.w
		h = self.size.h
		
		self.floor = 'plc:Stone_Block'
		self.wall = 'plc:Wall_Block'
		self.drawEmpty = False
		self.empty = 'plc:Plain_Block'
		self.corridor = 'plc:Wood_Block'
		self.door = 'plc:Door_Tall_Closed'
		self.coin = 'plf:HudCoin'
		self.numbers = 'plf:Hud'
		
		self.blocksAcross = 5
		self.blocksAlong = max(w, h) / min(w, h) * self.blocksAcross
		self.small = min(w, h)
		self.tileWidth = self.small / self.blocksAcross
		
	def loadControls(self):
		self.l = None # The location of the finger moving the player.
		self.moveTouch = None # The touch ID of the finger moving the player.
		self.ellipse = Rect(self.small * 0.05, self.small * 0.03, self.small * 0.4, self.small * 0.4) # The size of the corcle that the player can tap to move.
		self.ellipseCentre = Point(self.ellipse.x + (self.ellipse.w * 0.5), self.ellipse.y + (self.ellipse.h * 0.5))
		self.ellipseRadius = self.ellipse.w * 0.5
		
	def draw(self):
		w = self.size.w
		h = self.size.h
		if not self.loaded:
			background(0, 0, 0)
			text('Loading...', 'Futura', 50, w * 0.5, h * 0.5)
			return
			
		if self.state == 'Play':
			#t = time()
			self.drawGame()
			#print(time() - t)
			self.moveCharacter()
			self.player.update()
			self.updateEntities()
			#print(time() - t)
			#print()
			
			#print(str(self.player.getPoint()) + '    ' + str(self.player.getBottom()))
			
		if self.state == 'Death':
			self.drawDeathScreen()
			
	def drawGame(self):
		background(0, 0, 0)
		self.drawMap()
		self.drawHUD()
		
	def drawMap(self):
	
		x = self.player.x
		y = self.player.y
		w = self.size.w
		h = self.size.h
		tw = self.tileWidth
		
		cx = w * 0.5
		cy = h * 0.5
		
		halfWidth = tw * 0.5
		centerBlockX = cx - halfWidth
		centerBlockY = cy - halfWidth
		x_half = centerBlockX / tw
		y_half = centerBlockY / tw
		x_range = range(floor(x - x_half), ceil(x + x_half + 1))
		y_range = range(ceil(y + y_half + 1), floor(y - y_half - 1), -1)
		
		for tile_x in x_range:
			sx = (tile_x - x) * tw + centerBlockX
			for tile_y in y_range:
				
				sy = (tile_y - y) * tw + centerBlockY
					
				i = self.blockAt(tile_x, tile_y)
				if i == 0 and self.drawEmpty: # EMPTY:
					tint(0.3, 0.3, 0.3)
					image(self.empty, sx, sy, tw, tw - 1, 0, 20, 50, 40)
					tint(1, 1, 1)
				if i == 1: # FLOOR
					image(self.floor, sx, sy, tw, tw - 1, 0, 20, 50, 40)
				if i == 2: # CORRIDOR
					image(self.corridor, sx, sy, tw, tw - 1, 0, 20, 50, 40)
				if i == 3: # DOOR
					image(self.corridor, sx, sy, tw, tw - 1, 0, 20, 50, 40)
				if i == 5: # WALL:
					image(self.wall, sx, sy - (tw * 0.45), tw, tw * 2.05)
					
		for e in self.entities:
			if (x_range[0] <= ceil(e.x) and floor(e.x) <= x_range[-1]) and (y_range[0] >= floor(e.y ) and ceil(e.y) >= y_range[-1]):
				e.setTint()
				image(e.image, (e.x - x) * tw + centerBlockX, (e.y - y) * tw + centerBlockY, tw, tw)
		tint(1, 1, 1)
		self.player.setTint()
		image(self.player.image, centerBlockX, centerBlockY, tw, tw * 1.7)
		
	def drawHUD(self):
		w = self.size.w
		h = self.size.h
		tint(1, 1, 1)
		
		# Health Bar
		fill(1, 0, 0)
		rect(self.small * 0.4, h - self.small * 0.09, self.small * 0.5, self.small * 0.05)
		fill(0, 1, 0)
		rect(self.small * 0.4, h - self.small * 0.09, self.small * 0.5 * (self.player.health / self.player.maxHealth), self.small * 0.05)
		
		# Coins
		image(self.coin, self.small * 0.01, self.size.h - self.small * 0.11, self.small * 0.09, self.small * 0.09)
		c = str(int(round(self.player.coins)))
		for i in range(len(c)):
			image(self.numbers + c[i], self.small * (0.07 + (i * 0.04)), h - self.small * (0.105 + (int(c[i]) * 0.0003)), self.small * 0.09, self.small * 0.09)
			
		# Touch Circle
		fill(0.5, 0.5, 0.5, 0.5)
		ellipse(*self.ellipse)
		
		# Inventory
		if self.small == w: # Portrait mode
			sw = w * 0.15 # Square width
			bw = w * 0.01 # Border width
			fill(0.5, 0.5, 0.5, 0.5)
			x = w * 0.483
			y = w * 0.04
			rect(x, y, sw * 3 + bw * 4, sw * 2 + bw * 3)
			fill(1, 1, 1)
			for i in range(3):
				rect(x, y + i * (sw + bw), sw * 3 + bw * 4, bw)
			for i in range(4):
				rect(x + i * (sw + bw), y, bw, sw * 2 + bw * 3)
				
			for i in range(5):
				if self.player.inventory[i]:
					self.player.inventory[i].draw(x + (bw * (i % 3 + 1)) + (sw * (i % 3)), y + (bw * (2 - int(i / 3))) + (sw * (1 - int(i / 3))), sw)
					
					
					
	def drawDeathScreen(self):
		background(0, 0, 0)
		tint('red')
		text('WASTED', 'DIN Alternate', 50, self.size.w * 0.5, self.size.h * 0.5)
		
	def moveCharacter(self):
		w = self.size.w
		h = self.size.h
		s = self.dt * self.player.speed
		if self.l != None:
			l = self.l
			a = atan2(l.x - 100, l.y - 100)
			self.player.x += sin(a) * s
			dx = self.player.getLeft() % 1
			if dx < 0.5: # LEFT
				if not self.canWalk(self.player.getLeft(), self.player.getBottom()) or not self.canWalk(self.player.getLeft(), self.player.getTop()):
					self.player.x += (0.5 - dx)
			dx = self.player.getRight() % 1
			if 0.499 < dx: # RIGHT
				if not self.canWalk(self.player.getRight(), self.player.getBottom()) or not self.canWalk(self.player.getRight(), self.player.getTop()):
					self.player.x -= (dx - 0.499)
			self.player.y += cos(a) * s
			dy = self.player.getBottom() % 1
			if dy < 0.5: # DOWN
				if not self.canWalk(self.player.getLeft(), self.player.getBottom()) or not self.canWalk(self.player.getRight(), self.player.getBottom()):
					self.player.y += (0.5 - dy)
			dy = self.player.getTop() % 1
			if 0.499 < dy: # UP
				if not self.canWalk(self.player.getLeft(), self.player.getTop()) or not self.canWalk(self.player.getRight(), self.player.getTop()):
					self.player.y -= (dy - 0.499)
					
	def updateEntities(self):
		for e in self.entities:
			e.update(self)
		
	def touch_began(self, touch):
		w = self.size.w
		h = self.size.h
		l = touch.location
		if self.state == 'Play':
			if abs(l - self.ellipseCentre) <= self.ellipseRadius:
				self.moveTouch = touch.touch_id
				self.l = l
			else:
				cx = w * 0.5
				cy = h * 0.5
				
				halfWidth = self.tileWidth * 0.5
				centerBlockX = cx - halfWidth
				centerBlockY = cy - halfWidth
				
				ex = ((l.x - centerBlockX) / self.tileWidth) + self.player.x
				
				ey = ((l.y - centerBlockY) / self.tileWidth) + self.player.y
				
				for e in self.entities:
					if Point(ex, ey) in e.getRect():
						e.hurt(self.player.damage, self)
						break
						
	def touch_moved(self, touch):
		if self.state == 'Play':
			if self.l != None and self.moveTouch == touch.touch_id:
				self.l = touch.location
				
	def touch_ended(self, touch):
		if self.state == 'Play':
			if self.moveTouch == touch.touch_id:
				self.l = None
				self.moveTouch = None
		
class Player (object):
	def __init__(self, x, y):
		self.x = x
		self.y = y
		self.inventory = [None] * 5
		self.speed = 10 # Speed is in blocks per second, default 2.5
		self.health = 20
		self.maxHealth = 20
		self.damage = 2
		self.coins = 0
		self.newCoins = 1000
		self.coinCollectSpeed = lambda x: max(x / 5, 0.2) #max(x ** 0.85, 0.2)
		self.hurtStart = 0
		seed(time())
		self.image = 'plc:Character_Boy'
		
	def update(self):
		if self.newCoins > 0.4:
			self.coins += self.coinCollectSpeed(self.newCoins)
			self.newCoins -= self.coinCollectSpeed(self.newCoins)
		elif self.newCoins > 0:
			self.coins += self.newCoins
			self.coins = round(self.coins)
			self.newCoins = 0
			
	def receiveItem(self, item):
		for i in self.inventory:
			if i and i.name == item.name:
				i = i + item
				return
		if None in self.inventory:
			self.inventory[self.inventory.index(None)] = item
			
	def recieveItems(self, *items):
		for item in items: self.receiveItem(item)
		
	def receiveCoins(self, coins):
		self.newCoins += coins
		
	def canWalk(self, block):
		return 0 < block < 4
		
	def hurt(self, damage, game):
		self.health -= damage
		if self.health <= 0:
			game.state = 'Death'
		self.hurtStart = time()
		
	def setTint(self):
		tint(1, min(1, time() - self.hurtStart), min(1, time() - self.hurtStart))
		
	def getPoint(self):
		return Point(self.x, self.y)
		
	def getRect(self):
		return Rect(self.getLeft(), self.getBottom(), 0.7, 0.8)
		
	def getLeft(self):
		return self.x - 0.35
		
	def getRight(self):
		return self.x + 0.35
		
	def getBottom(self):
		return self.y - 0.2
		
	def getTop(self):
		return self.y + 0.6
		
class Enemy (object):
	def __init__(self, x, y, room):
		self.timer = 1000
		self.x = x
		self.y = y
		self.room = room
		self.hurtStart = 0
		self.hurtTimer = 0.5 # How many seconds the entity takes to go from its red hurt colour back to normal
		
	def getRect(self):
		return Rect(self.x, self.y, self.width, self.width)
		
	def hurt(self, damage, game):
		self.health -= damage
		if self.health <= 0:
			game.player.receiveCoins(self.coinsDropped)
			game.player.recieveItems(self.getDrops())
			game.entities.remove(self)
		self.hurtStart = time()
		
	def setTint(self):
		tint(1, min(1, (time() - self.hurtStart) / self.hurtTimer), min(1, (time() - self.hurtStart) / self.hurtTimer))
		
	def update(self, game):
		if not game.player.getRect().intersects(self.room.rect):
			return
		s = game.dt * self.speed
		d = atan2(game.player.x - self.x, game.player.y - self.y)
		if abs(game.player.getPoint() - Point(self.x, self.y)) > 0.7:
			if self.timer < 1:
				self.timer += game.dt
				return
			self.far = True
			self.x += sin(d) * s
			self.y += cos(d) * s
			
			if self.x < self.room.x:
				self.x = self.room.x
			if self.x > self.room.x + self.room.width:
				self.x = self.room.x + self.room.width
			if self.y < self.room.y:
				self.y = self.room.y
			if self.y > self.room.y + self.room.height:
				self.y = self.room.y + self.room.height
				
		else:
			self.far = False
			if self.timer >= 1:
				game.player.hurt(self.damage, game)
				self.timer = 0
			else:
				self.timer += game.dt
				
				
class Skull(Enemy):
	def __init__(self, x, y, room):
		Enemy.__init__(self, x, y, room)
		self.damage = 2
		self.maxHealth = 10
		self.coinsDropped = 5
		self.speed = 1
		self.health = self.maxHealth
		self.width = 1
		self.image = 'emj:Skull'
		
	def getDrops(self):
		return Bone(choice([1, 1, 1, 2, 2, 3]))
		
class Slime(Enemy):
	def __init__(self, x, y, room):
		Enemy.__init__(self, x, y, room)
		self.damage = 3
		self.maxHealth = 15
		self.coinsDropped = 10
		self.speed = 1.2
		self.health = self.maxHealth
		self.width = 1
		self.image = 'plf:Enemy_Slime' + choice(['Blue'])
		
	def getDrops(self):
		return None
		
class Item (object):
	def __init__(self, amount=1):
		self.amount = amount
		self.name = self.__class__.__name__
		
	def __add__(self, other):
		self.amount += other.amount
		return self
		
	def __mul__(self, other):
		self.amount = other
		return self
		
	def __repr__(self):
		return self.name + ' x' + str(self.amount)
		
	def draw(self, x, y, w):
		self.drawItem(x, y, w)
		if self.amount > 1:
			text(str(self.amount), 'Arial', 15, x + w, y + w, 1)
			
	def drawItem(self):
		pass
		
class Bone (Item):
	def drawItem(self, x, y, w):
		fill(1, 1, 1)
		push_matrix()
		translate(x + w * 0.5, y + w * 0.5)
		rotate(45)
		ellipse(w * -0.2, w * 0.3, w * 0.2, w * 0.2)
		ellipse(0, w * 0.3, w * 0.2, w * 0.2)
		rect(w * -0.1, w * -0.4, w * 0.2, w * 0.8)
		ellipse(w * -0.2, w * -0.5, w * 0.2, w * 0.2)
		ellipse(0, w * -0.5, w * 0.2, w * 0.2)
		pop_matrix()
		
		
run(DungeonGame(), show_fps=True)

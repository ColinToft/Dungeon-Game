import dungeonGenerator

from scene import *
from console import set_font
from random import choice, randint, randrange, seed
from math import atan2, ceil, cos, floor, sin
from re import findall
from time import time
import sound

# Version 0.2 build 3
# Colin Toft the code master
# Dylan Peters who did make it a bit better

EMPTY = 0
FLOOR = 1
CORRIDOR = 2
DOOR = 3
DOOR_LOCKED = 4
WALL = 5
OBSTACLE = 6
CAVE = 7
CHEST_CLOSED = 8
CHEST_OPEN = 9
CHEST_EMPTY = 10

# Room Types (Negative numbers mean rooms don't have enemies)

START = -1
END = -2

SKULL = 1
BLUE_SLIME = 2
GREEN_SLIME = 3
PURPLE_SLIME = 4

# Item Categories
WEAPONS = 0
ARMOR = 1
TOOLS = 2

class DungeonGame (Scene):
	def setup(self):
		self.loaded = False
		self.mapSize = 35  # Small: 35, Medium: 55, Large: 70
		self.entities = []
		
		self.loadGraphics()
		self.loadSound()
		self.loadItems()
		self.loadControls()
		
		r = randint(1, 10000000)
		self.generateMap(r)
		print(r)
		self.spawnPlayer()
		
		self.printMap()
		
		self.state = 'Play'
		self.loaded = True
		
	def generateMap(self, s=-1):
		if s > 0:
			seed(s)
		self.d = dungeonGenerator.dungeonGenerator(self.mapSize, self.mapSize)
		self.d.placeRandomRooms(5, 11, roomStep=1, margin=2, attempts=30000)
		self.d.generateCorridors('f')
		self.d.connectAllRooms(20)
		
		unconnected = self.d.findUnconnectedAreas()
		if unconnected:
			self.d.joinUnconnectedAreas(unconnected)
		
		DEADEND_COUNT = 3
		self.d.findDeadends()
		while len(self.d.deadends) > DEADEND_COUNT:
			self.d.pruneDeadends(1)
			
		self.d.placeWalls()
		
		self.map = self.d.grid
		self.rooms = self.d.rooms
		
		for i, r in enumerate(self.rooms):
			r.rect = Rect(r.x, r.y, r.width, r.height)
			r.type = choice([SKULL, SKULL, SKULL, BLUE_SLIME, GREEN_SLIME, PURPLE_SLIME])
			r.entities = []
			r.id = i
			r.area = r.width * r.height
			
		roomsBySize = sorted(self.rooms, key=lambda x: x.area)
		roomsBySize[0].type = START
		roomsBySize[-1].type = END
		
		self.chestContents = {}
		keysToPlace = 2
		for r in self.rooms:
			if r.type > 0:
				for i in range(randint(2, 4)):
					e = self.getEntityForRoom(r, randrange(r.x, r.x + r.width), randrange(r.y, r.y + r.height))
					
					self.entities.append(e)
					r.entities.append(e)
				
				while True:
					chestOnLeftRight = True if randint(0, 1) == 1 else False
					if chestOnLeftRight:
						chestX = choice([r.x, r.x + r.width - 1])
						chestY = randint(r.y, r.y + r.height - 1)
					else:
						chestX = randint(r.x, r.x + r.width - 1)
						chestY = choice([r.y, r.y + r.height - 1])
						
					# if chest is blocking a door or corridor, choose a new spot
					if not all(self.blockAt(*n) in [WALL, FLOOR] for n in self.d.findNeighboursDirect(chestX, chestY)):
						continue
						
					self.setBlock(chestX, chestY, CHEST_CLOSED)
					self.chestContents[(chestX, chestY)] = [choice([Wood(randint(1, 3)), Stone(randint(1, 3))])]
					if keysToPlace > 0:
						self.chestContents[(chestX, chestY)].append(Key())
						keysToPlace -= 1
						
					r.allDead = False
					break
					
			if r.type == END: # Lock doors to boss room
				for x in range(r.x - 1, r.x + r.width + 1):
					for y in range(r.y - 1, r.y + r.height + 1):
						if self.blockAt(x, y) == DOOR:
							self.setBlock(x, y, DOOR_LOCKED)
					
		# maps blocks to rooms, positive numbers are the id of the room the block is in, negative numbers are for corridors (corridors are also given an id)
		# room ids are sets because some walls can be adjacent to a room and a corridor
		self.roomMap = [[set() for y in range(self.mapSize)] for x in range(self.mapSize)]
		
		for r in self.rooms:
			for x in range(r.x - 1, r.x + r.width + 1): # add boundary for wall
				for y in range(r.y - 1, r.y + r.height + 1):
					if 0 < x < self.mapSize and 0 < y < self.mapSize:
						if not self.blockAt(x, y) == DOOR:
							self.roomMap[x][y].add(r.id)
						
						
		for x in range(self.mapSize):
			for y in range(self.mapSize):
				if self.d.grid[x][y] == CORRIDOR:
					for n in self.d.findNeighboursDirect(x, y):
						if self.d.grid[n[0]][n[1]] == FLOOR:
							self.d.grid[x][y] = DOOR
							
		
		corridors = [(x, y) for x in range(self.mapSize) for y in range(self.mapSize) if self.blockAt(x, y) == CORRIDOR]
		id = len(self.rooms)
		while corridors:
			next = [corridors.pop()]
			while next:
				self.roomMap[next[-1][0]][next[-1][1]].add(id)
				if next[-1] in corridors: corridors.remove(next[-1])
				for tile in self.d.findNeighbours(*next.pop()):
					self.roomMap[tile[0]][tile[1]].add(id)
					if self.blockAt(*tile) == CORRIDOR and tile in corridors:
						next.append(tile)
						corridors.remove(tile)
			
			id += 1
			
		self.roomBrightnesses = [self.darkTint for i in range(id)]
			
		if self.d.deadends:
			for d in self.d.deadends:
				self.d.grid[d[0]][d[1]] = CHEST_OPEN
				self.chestContents[d] = [choice([Wood(randint(1, 3)), Stone(randint(1, 3))])]
		
			
	def getEntityForRoom(self, room, x, y):
		if room.type == SKULL:
			return Skull(x, y, room)
		elif room.type == BLUE_SLIME:
			return BlueSlime(x, y, room)
		elif room.type == GREEN_SLIME:
			return GreenSlime(x, y, room)
		elif room.type == PURPLE_SLIME:
			return PurpleSlime(x, y, room)
			
	def spawnPlayer(self):
		playerRoom = [r for r in self.rooms if r.type == START][0]
		x = playerRoom.x
		y = playerRoom.y
		wid = playerRoom.width
		hei = playerRoom.height
		self.player = Player(x + wid / 2, y + hei / 2)
		
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
		t = ['#', ' ', '•', '=', '~', '%', '*', 'C', '$', '€', '£']
		
		print(f'{len(self.rooms)} rooms')
		
		set_font('Menlo', self.size.h * 0.87 / self.mapSize)
		
		# Use the star to represent the player.
		self.setBlock(self.player.x, self.player.y, 6)
		
		s = ''
		for y in range(self.mapSize - 1, -1, -1):
			for x in range(0, self.mapSize):
				s += t[self.map[x][y]]
			s += '\n'
		print(s)
		
		self.setBlock(self.player.x, self.player.y, FLOOR)
		
	def blockAt(self, x, y):
		if x < 0 or y < 0: return EMPTY
		try:
			return self.map[floor(x)][floor(y)]
		except IndexError:
			return EMPTY
			
	def roomAt(self, x, y):
		if x < 0 or y < 0: return set()
		try:
			return self.roomMap[floor(x)][floor(y)]
		except IndexError:
			return set()
			
	def setBlock(self, x, y, block):
		if x < 0 or y < 0: return False
		try:
			self.map[floor(x)][floor(y)] = block
			return True
		except IndexError:
			return False
			
	def canWalk(self, x, y):
		return self.player.canWalk(self.blockAt(x, y))
		
	def loadGraphics(self):
		w = self.size.w
		h = self.size.h
		
		self.floor = 'plc:Stone_Block'
		self.wall = 'plc:Wall_Block'
		self.drawEmpty = True
		self.empty = 'plc:Water_Block'
		self.corridor = 'plc:Wood_Block'
		self.door = 'plc:Door_Tall_Closed'
		self.coin = 'plf:HudCoin'
		self.chestClosed = 'plc:Chest_Closed'
		self.chestOpen = 'plc:Chest_Open'
		self.numbers = 'plf:Hud'
		
		self.blocksAcross = 5
		self.blocksAlong = max(w, h) / min(w, h) * self.blocksAcross
		self.small = min(w, h)
		self.tileWidth = self.small / self.blocksAcross
		
		self.darkTint = 0.35
		self.fadeSpeed = 0.4
		
	def loadSound(self):
		self.useSound = True
		if self.useSound:
			self.soundPlayer = sound.Player('Dungeon Game 1.wav')
			self.soundPlayer.play()
		
	def loadControls(self):
		self.l = None # The location of the finger moving the player.
		self.moveTouch = None # The touch ID of the finger moving the player.
		self.ellipse = Rect(self.small * 0.05, self.small * 0.03, self.small * 0.4, self.small * 0.4) # The size of the corcle that the player can tap to move.
		self.ellipseCentre = Point(self.ellipse.x + (self.ellipse.w * 0.5), self.ellipse.y + (self.ellipse.h * 0.5))
		self.ellipseRadius = self.ellipse.w * 0.5
		
	def loadItems(self):
		w = self.size.w
		h = self.size.h
		
		self.craftingTabs = [[] for i in range(3)]
		self.craftableItems = [BoneDagger(), WoodenShield(), Bomb()]
		for item in self.craftableItems:
			self.craftingTabs[item.getCategory()].append(item)
		self.selectedItem = None
		self.selectedCraftingItem = None
		
		self.craftButton = SpriteNode('pzl:Button1', parent=self)
		
		button_font = ('DIN Alternate', 20)
		self.craftButton.title_label = LabelNode('Craft', font=button_font, color='black', position=(0, 1), parent=self.craftButton)
		self.craftButton.position = self.size.w * 0.75, self.size.h * 0.05
		self.craftButton.size = w * 0.3, h * 0.06
		self.craftButton.alpha = 0
		
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
			self.player.update(self)
			self.updateEntities()
			#print(time() - t)
			#print()
			#print(str(self.player.x) + ' ' + str(self.player.y))
			
		elif self.state == 'Inventory':
			self.drawInventoryScreen()
			
		elif self.state == 'Death':
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
		x_half = cx / tw
		y_half = cy / tw
		x_range = range(floor(x - x_half), ceil(x + x_half + 1))
		y_range = range(ceil(y + y_half), floor(y - y_half - 1), -1)
		
		for room in range(len(self.roomBrightnesses)):
			if room in self.roomAt(x, y):
				self.roomBrightnesses[room] = min(1, self.roomBrightnesses[room] + 1 / self.fadeSpeed * self.dt)
			elif room >= len(self.rooms) or not hasattr(self.rooms[room], 'allDead') or not self.rooms[room].allDead:
				self.roomBrightnesses[room] = max(self.darkTint, self.roomBrightnesses[room] - 1 / self.fadeSpeed * self.dt)
			
		for tile_x in x_range:
			sx = (tile_x - x) * tw + cx
			for tile_y in y_range:
				
				sy = (tile_y - y) * tw + cy
					
				try:
					tint(*(max([self.roomBrightnesses[r] for r in self.roomAt(tile_x, tile_y)]) for i in range(3)))
				except ValueError:
					tint(0.35, 0.35, 0.35)
					
				i = self.blockAt(tile_x, tile_y)
				
				if i == EMPTY and self.drawEmpty: 
					image(self.empty, sx, sy, tw, tw, 0, 20, 50, 40)
				if i == FLOOR:
					image(self.floor, sx, sy, tw, tw, 0, 20, 50, 40)
				if i == CORRIDOR:
					image(self.corridor, sx, sy, tw, tw, 0, 20, 50, 40)
				if i == DOOR or i == DOOR_LOCKED:
					image(self.door, sx, sy, tw, tw, 0, 10, 50, 36)
				if i == WALL:
					image(self.wall, sx, sy - (tw * 0.45), tw, tw * 2.05)
				if i == CHEST_CLOSED:
					image(self.floor, sx, sy, tw, tw, 0, 20, 50, 40)
					image(self.chestClosed, sx, sy, tw, tw, 0, 0, 50, 60)
				if i == CHEST_OPEN:
					image(self.floor, sx, sy, tw, tw, 0, 20, 50, 40)
					image(self.chestOpen, sx, sy, tw, tw, 0, 0, 50, 60)
					contents = self.chestContents[(tile_x, tile_y)]
					usableW = tw * 0.9
					bw = tw * 0.01
					itemW = min(tw * 0.5, (usableW - (bw * len(contents))) / len(contents))
					totalW = itemW * len(contents) + bw * (len(contents) - 1)
					startX = (usableW - totalW) * 0.5
					for i in range(len(contents)):
						contents[i].draw(sx + (tw - usableW) * 0.5 + startX + ((itemW + bw) * i), sy + tw * 0.68 - itemW * 0.5, itemW, num=False)
						
				if i == CHEST_EMPTY:
					image(self.floor, sx, sy, tw, tw, 0, 20, 50, 40)
					image(self.chestOpen, sx, sy, tw, tw, 0, 0, 50, 60)
					
					
		for e in self.entities:
			if (x_range[0] <= ceil(e.x) and floor(e.x) <= x_range[-1]) and (y_range[0] >= floor(e.y) and ceil(e.y) >= y_range[-1]):
				if e.room.id in self.roomAt(x, y): # only show entities if player is in the room
					e.setTint()
					image(e.image, (e.x - x) * tw + cx, (e.y - y) * tw + cy, tw, tw)
				
		self.player.setTint()
		image(self.player.image, cx - halfWidth, cy - halfWidth, tw, tw * 1.7)
		
	def drawHUD(self):
		w = self.size.w
		h = self.size.h
		tint(1, 1, 1)
		
		# Health Bar
		fill(1, 0, 0)
		rect(self.small * 0.4, h - self.small * 0.09, self.small * 0.5, self.small * 0.05)
		fill(0, 1, 0)
		rect(self.small * 0.4, h - self.small * 0.09, self.small * 0.5 * max(self.player.health / self.player.maxHealth, 0), self.small * 0.05)
		
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
			self.drawGrid(3, 2, w * 0.483, w * 0.04, w * 0.49, w * 0.01, items=self.player.inventory[:5] + ['iow:ios7_more_256'], selected=self.selectedItem, squareFill=(0.5, 0.5, 0.5, 0.5))
			
	def drawGrid(self, tile_w, tile_h, x, y, w, bw, items=[], selected=None, squareFill=(1, 1, 1, 0), borderFill=(1, 1, 1)):
		items = list(items)
		while items and items[-1] == None: items.pop()
		sw = (w - (bw * tile_w) - bw) / tile_w # Square width
		fill(*squareFill)
		rect(x, y, w, (sw + bw) * tile_h + bw)
		fill(borderFill)
		for i in range(tile_h + 1):
			rect(x, y + i * (sw + bw), (bw + sw) * tile_w + bw, bw)
		fill(borderFill)
		for i in range(tile_w + 1):
			rect(x + i * (sw + bw), y, bw, (bw + sw) * tile_h + bw)
		for i, item in enumerate(items):
			if item is None and not i == selected: continue
			imageX = x + bw + (i % tile_w) * (bw + sw)
			imageY = y - sw + (tile_h - int(i / tile_w)) * (bw + sw)
			if isinstance(item, Item):
				item.draw(imageX, imageY, sw)
			elif isinstance(item, str):
				image(item, imageX, imageY, sw, sw)
			
			if selected == i:
				rect(imageX - bw * 1.5, imageY - bw * 1.5, bw * 1.5, sw + bw * 3)
				rect(imageX + sw, imageY - bw * 1.5, bw * 1.5, sw + bw * 3)
				rect(imageX, imageY - bw * 1.5, sw, bw * 1.5)
				rect(imageX, imageY + sw, sw, bw * 1.5)

				
				
	def touchedSquare(self, l, tile_w, tile_h, x, y, w, bw):
		sw = (w - (bw * tile_w) - bw) / tile_w # Square width
		for i in range(tile_w * tile_h):
			squareX = x + bw + (i % tile_w) * (bw + sw)
			squareY = y - sw + (tile_h - int(i / tile_w)) * (bw + sw)
			if l in Rect(squareX, squareY, sw, sw):
				return i
		return None
				
	def drawItemList(self):
		pass
					
	def drawInventoryScreen(self):
		w = self.size.w
		h = self.size.h
		
		background(0.6, 0.6, 0.6)
		text('Inventory', 'DIN Alternate', 40, w * 0.5, h, alignment=2)
		text('Back', 'DIN Alternate', 30, 5, h - 3, alignment=3)
		
		self.drawGrid(6, 4, 0, h * 0.535, w, w * 0.01, items=self.player.inventory)
		
		if self.inventoryMode == 'Crafting':
			text('Crafting', 'DIN Alternate', 40, w * 0.5, h * 0.49)
			self.drawGrid(3, 4, 0, 0, w * 0.5, w * 0.01, items=self.craftingTabs[self.currentTab], selected=self.selectedCraftingItem)
			
			try:
				itemToCraft = self.craftingTabs[self.currentTab][self.selectedCraftingItem]
				
				text(itemToCraft.name, 'DIN Alternate', 25, w * 0.75, h * 0.359)
				
				self.drawGrid(3, 2, w * 0.5, h * 0.14, w * 0.5, bw=0, items=itemToCraft.getRecipe(), borderFill=(0, 0, 0, 0))
				
			except IndexError:
				pass
			except TypeError: # selectedCraftingItem is None
				pass
			
		else:
			image(self.player.image, 0, h * 0.12, w * 0.4, w * 0.4 * 1.7)
		
		#rect(w * 0.4, 0, bw, h * 0.45)
		#rect(w - bw, 0, bw, h * 0.45)
		#rh = h * 0.15
		#for i, item in enumerate(self.craftableItems):
			#x = w * 0.4
			#y = h * 0.45 - (bw * (i + 0)) - (rh * (i + 0))
			#rect(w * 0.4, y, w * 0.6, bw)
			#item.drawItem(x, y, rh)
			
		#rect(w * 0.4, h * 0.45 - bw, w * 0.6, bw)
					
	def drawDeathScreen(self):
		background(0, 0, 0)
		tint('red')
		text('WASTED', 'DIN Alternate', 50, self.size.w * 0.5, self.size.h * 0.5)
		
	def moveCharacter(self):
		s = self.dt * self.player.speed
		
		SMALL = 0.0001
		
		if self.l != None:
			l = self.l
			a = atan2(l.x - 100, l.y - 100)
			
			self.player.x += sin(a) * s
			dx = self.player.getLeft() % 1
			if not self.canWalk(self.player.getLeft(), self.player.getBottom()) or not self.canWalk(self.player.getLeft(), self.player.getTop()): # LEFT
				self.player.x += 1 - dx + SMALL
				
			dx = self.player.getRight() % 1
			if not self.canWalk(self.player.getRight(), self.player.getBottom()) or not self.canWalk(self.player.getRight(), self.player.getTop()): # RIGHT
				self.player.x -= dx + SMALL
					
			self.player.y += cos(a) * s
			dy = self.player.getBottom() % 1
			if not self.canWalk(self.player.getLeft(), self.player.getBottom()) or not self.canWalk(self.player.getRight(), self.player.getBottom()): # DOWN
				self.player.y += 1 - dy + SMALL
				
			dy = self.player.getTop() % 1
			if not self.canWalk(self.player.getLeft(), self.player.getTop()) or not self.canWalk(self.player.getRight(), self.player.getTop()): # UP
				self.player.y -= dy + SMALL
					
	def updateEntities(self):
		for e in self.entities:
			e.update(self)
		
	def touch_began(self, touch):
		w = self.size.w
		h = self.size.h
		l = touch.location
		if self.state == 'Play':
			square = self.touchedSquare(l, 3, 2, w * 0.483, w * 0.04, w * 0.49, w * 0.01)
			if square in range(5):
				self.selectedItem = square
			elif square == 5:
				self.inventoryMode = 'Crafting'
				self.state = 'Inventory'
				self.currentTab = 0  # First tab
				self.craftButton.alpha = 0.5
			
			if abs(l - self.ellipseCentre) <= self.ellipseRadius:
				self.moveTouch = touch.touch_id
				self.l = l
			else:
				cx = w * 0.5
				cy = h * 0.5
				
				ex = ((l.x - cx) / self.tileWidth) + self.player.x
				ey = ((l.y - cy) / self.tileWidth) + self.player.y
				
				for e in self.entities:
					if Point(ex, ey) in e.getRect():
						if abs(e.getCenterpoint() -self.player.getCenterpoint()) < self.player.getRange(self.selectedItem):
							if self.player.getRect().intersects(e.room.rect):
								e.hurt(self.player.getDamage(self.selectedItem), self)
								break
				
				if self.blockAt(ex, ey) == CHEST_OPEN:
					self.player.receiveItems(*self.chestContents[(floor(ex), floor(ey))])
					self.chestContents[(floor(ex), floor(ey))] = []
					self.setBlock(ex, ey, CHEST_EMPTY)
					
				elif self.blockAt(ex, ey) == DOOR_LOCKED:
					if isinstance(self.player.inventory[self.selectedItem], Key):
						self.setBlock(ex, ey, DOOR)
						self.player.subtractItems([Key()])
				
		elif self.state == 'Inventory':
			if l in Rect(0, h * 0.92, w * 0.2, h * 0.08):
				self.state = 'Play'
				self.craftButton.alpha = 0
			
			x = self.touchedSquare(l, 3, 4, 0, 0, w * 0.5, w * 0.01)
			if x is not None:
				self.selectedCraftingItem = x
				try:
					itemToCraft = self.craftingTabs[self.currentTab][self.selectedCraftingItem]
					if self.player.hasItems(itemToCraft.getRecipe()):
						self.craftButton.alpha = 1
					else:
						self.craftButton.alpha = 0.5
				except IndexError: pass
				except TypeError: pass
				
			if l in self.craftButton.frame:
				try:
					itemToCraft = self.craftingTabs[self.currentTab][self.selectedCraftingItem]
					if self.player.hasItems(itemToCraft.getRecipe()):
						self.craftButton.texture = Texture('pzl:Button2')
						self.craftButton.size = w * 0.3, h * 0.06
				except IndexError: pass
				except TypeError: pass
			
		elif self.state == 'Death':
			self.state = 'Play'
			self.l = None
			self.moveTouch = None
			self.spawnPlayer()
						
	def touch_moved(self, touch):
		if self.state == 'Play':
			if self.l != None and self.moveTouch == touch.touch_id:
				self.l = touch.location
				
	def touch_ended(self, touch):
		w = self.size.w
		h = self.size.h
		l = touch.location
		
		if self.state == 'Play':
			if self.moveTouch == touch.touch_id:
				self.l = None
				self.moveTouch = None
				
		elif self.state == 'Inventory':
			self.craftButton.texture = Texture('pzl:Button1')
			self.craftButton.size = w * 0.3, h * 0.06
			try:
				itemToCraft = self.craftingTabs[self.currentTab][self.selectedCraftingItem]
				
				if l in self.craftButton.frame and self.player.hasItems(itemToCraft.getRecipe()):
					self.player.subtractItems(itemToCraft.getRecipe())
					self.player.receiveItem(itemToCraft.copy())
			except TypeError:
				pass
			except IndexError:
				pass
			
	def did_change_size(self):
		print('woah')
		
	def pause(self):
		print('bye')
		self.soundPlayer.pause()
		
	def stop(self):
		self.pause()
		
class Player (object):
	def __init__(self, x, y):
		self.x = x
		self.y = y 
		self.inventory = [None] * 24
		self.speed = 4 # Speed is in blocks per second, default 4
		self.health = 20
		self.maxHealth = 20
		self.healSpeed = 0.5
		self.damage = 2
		self.range = 2
		self.coins = 0
		self.newCoins = 0
		self.coinCollectSpeed = lambda x: max(x / 7, 0.2) #max(x ** 0.85, 0.2)
		self.hurtTime = 9999
		seed(time())
		self.image = 'plc:Character_Boy'
		self.lastUpdate = time()
		
	def update(self, game):
		if self.newCoins > 0.4:
			self.coins += self.coinCollectSpeed(self.newCoins)
			self.newCoins -= self.coinCollectSpeed(self.newCoins)
		elif self.newCoins > 0:
			self.coins += self.newCoins
			self.coins = round(self.coins)
			self.newCoins = 0
			
		if self.hurtTime > 10:
			self.heal(self.healSpeed * (time() - self.lastUpdate))
			
		self.hurtTime += game.dt
		self.lastUpdate = time()
			
	def receiveItem(self, item):
		for i in self.inventory:
			if i and i.name == item.name:
				i = i + item
				return
		if None in self.inventory:
			self.inventory[self.inventory.index(None)] = item
			
	def receiveItems(self, *items):
		for item in items: self.receiveItem(item)
		
	def receiveCoins(self, coins):
		self.newCoins += coins
		
	def hasItems(self, itemList):
		for item in itemList:
			if not any(type(playerItem) == type(item) and (playerItem >= item) for playerItem in self.inventory):
				return False
		return True
			
	def subtractItems(self, itemList):
		for item in itemList:
			for playerItem in self.inventory:
				if type(item) == type(playerItem):
					self.inventory[self.inventory.index(playerItem)] -= item
					if self.inventory[self.inventory.index(playerItem)] .amount == 0:
						self.inventory[self.inventory.index(playerItem)] = None
					
	def canWalk(self, block):
		return 0 < block < 4
		
	def hurt(self, damage, game):
		self.health -= damage
		if self.health <= 0:
			game.state = 'Death'
		self.hurtTime = 0
		
	def heal(self, regen):
		self.health = min(self.maxHealth, self.health + regen)
		
	def setTint(self):
		tint(1, min(1, self.hurtTime), min(1, self.hurtTime))
		
	def getDamage(self, selectedItem):
		if selectedItem is not None:
			if isinstance(self.inventory[selectedItem], Weapon):
				return self.inventory[selectedItem].getDamage()
		return self.damage
		
	def getRange(self, selectedItem):
		return self.range
		
	def getCenterpoint(self):
		return self.getRect().center()

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
		self.x = x # Lower left coordinates
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
			game.player.receiveItems(self.getDrops())
			game.entities.remove(self)
			self.room.entities.remove(self)
			if len(self.room.entities) == 0:
				self.room.allDead = True
				for x in range(self.room.x, self.room.x + self.room.width):
					for y in range(self.room.y, self.room.y + self.room.height):
						if game.blockAt(x, y) == CHEST_CLOSED:
							game.map[x][y] = CHEST_OPEN
				
		self.hurtStart = time()
		
	def setTint(self):
		tint(1, min(1, (time() - self.hurtStart) / self.hurtTimer), min(1, (time() - self.hurtStart) / self.hurtTimer))
		
	def update(self, game):
		if self.room.id not in game.roomAt(game.player.x, game.player.y):
			return
		s = game.dt * self.speed
		d = atan2(game.player.x - self.x, game.player.y - self.y)
		if abs(game.player.getCenterpoint() - self.getCenterpoint()) > 0.7:
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
				
	def getCenterpoint(self):
		return self.getRect().center()
				
				
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
		self.speed = 1.2
		self.health = self.maxHealth
		self.width = 1
		self.image = 'plf:Enemy_Slime' + self.colour
		
	def getDrops(self):
		return Gel.getGel(self.colour, 1)
		
class BlueSlime (Slime):
	def __init__(self, x, y, room):
		self.colour = 'Blue'
		self.damage = 3
		self.maxHealth = 12
		self.coinsDropped = 10
		Slime.__init__(self, x, y, room)
		
class GreenSlime (Slime):
	def __init__(self, x, y, room):
		self.colour = 'Green'
		self.damage = 4
		self.maxHealth = 15
		self.coinsDropped = 15
		Slime.__init__(self, x, y, room)
		
class PurpleSlime (Slime):
	def __init__(self, x, y, room):
		self.colour = 'Purple'
		self.damage = 5
		self.maxHealth = 20
		self.coinsDropped = 20
		Slime.__init__(self, x, y, room)
	
class Item (object):
	def __init__(self, amount=1):
		self.amount = amount
		self.name = ' '.join(findall('[A-Z][^A-Z]*', self.__class__.__name__)) # Split apart camel casing to get the item name from the class name
		
	def __add__(self, other):
		self.amount += other.amount
		return self
		
	def __sub__(self, other):
		self.amount -= other.amount
		return self	
		
	def __gt__(self, other):
		return self.amount > other.amount
		
	def __ge__(self, other):
		return self.amount >= other.amount
		
	def __repr__(self):
		return self.name + ' x' + str(self.amount)
		
	def copy(self):
		c = self.__class__
		return c()
		
	def draw(self, x, y, w, num=True):
		self.drawItem(x + w * 0.2, y + w * 0.2, w * 0.6)
		if self.amount > 1 and num:
			text(str(self.amount), 'Arial', 15, x + w * 0.98, y + w, 1)
			
	def drawItem(self, x, y, z):
		pass
		
class CraftableItem (Item):
	def getRecipe(self):
		return self.recipe
		
	def getCategory(self):
		return self.category
		
class Weapon (object):
	def getDamage(self):
		return self.damage
	
	def getRange(self):
		return self.range
		
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
		
class Gel (Item):
	def __init__(self, amount):
		Item.__init__(self, amount)
		
	def getGel(colour, amount):
		if colour == 'Green': return GreenGel(amount)
		elif colour == 'Blue': return BlueGel(amount)
		elif colour == 'Purple': return PurpleGel(amount)
		
	def drawItem(self, x, y, w):
		tint(*self.colour)
		image('pzl:BallGray', x, y, w, w)
		tint('white')
		
class GreenGel (Gel):
	def __init__(self, amount):
		Gel.__init__(self, amount)
		self.colour = (0, 1, 0)
		
class BlueGel (Gel):
	def __init__(self, amount):
		Gel.__init__(self, amount)
		self.colour = (0, 0.5, 1)
		
class PurpleGel (Gel):
	def __init__(self, amount):	
		Gel.__init__(self, amount)
		self.colour = (1, 0.4, 1)
		
class Wood (Item):
	def drawItem(self, x, y, w):
		image('plc:Wood_Block', x, y, w, w, 0, 20, 50, 40)
	
class Stone (Item):
	def drawItem(self, x, y, w):
		image('plc:Rock', x, y, w, w * 1.4)
		
class Key (Item):
	def drawItem(self, x, y, w):
		image('Key', x, y, w, w)
		
class BoneDagger (CraftableItem, Weapon):
	def __init__(self, amount=1):
		CraftableItem.__init__(self, amount)
		self.category = WEAPONS
		self.recipe = [Wood(1), Bone(1)]
		self.damage = 3.5
		self.range = 2
		
	def drawItem(self, x, y, w):
		image('plf:SwordSilver', x, y, w, w)
		
class WoodenShield (CraftableItem):
	def __init__(self, amount=1):
		CraftableItem.__init__(self, amount)
		self.category = ARMOR
		self.recipe = [Wood(3)]
		
	def drawItem(self, x, y, w):
		image('plf:ShieldBronze', x, y, w, w)
		
class Bomb (CraftableItem):
	def __init__(self, amount=1):
		CraftableItem.__init__(self, amount)
		self.category = WEAPONS
		self.recipe = [BlueGel(2), GreenGel(1)]
		
	def drawItem(self, x, y, w):
		image('Bomb', x, y, w, w)
	
		
run(DungeonGame(), show_fps=True)

---@meta

---@class WeGraphics
local WeGraphics = {}

---@param x number
---@param y number
---@param w number
---@param h number
---@param color string
---@param width? integer
function WeGraphics.draw_rect(x, y, w, h, color, width) end

---@param x number
---@param y number
---@param radius number
---@param color string
---@param width? integer
function WeGraphics.draw_circle(x, y, radius, color, width) end

---@param x1 number
---@param y1 number
---@param x2 number
---@param y2 number
---@param color string
---@param width? integer
function WeGraphics.draw_line(x1, y1, x2, y2, color, width) end

---@class WeInput
local WeInput = {}

---@param key_name string
---@return boolean
function WeInput.pressed(key_name) end

---@class WeDebug
local WeDebug = {}

---@param message string
function WeDebug.log(message) end

---@class ColliderStub

---@class GameObjectStub
---@field name string

---@class WePhysics
local WePhysics = {}

---@param first ColliderStub
---@param second ColliderStub
---@return boolean
function WePhysics.overlaps(first, second) end

---@param collider ColliderStub
---@return GameObjectStub[]
function WePhysics.query_overlaps(collider) end

---@class WeApi
---@field graphics WeGraphics
---@field input WeInput
---@field debug WeDebug
---@field physics WePhysics
we = {}

---@type WeGraphics
we.graphics = WeGraphics

---@type WeInput
we.input = WeInput

---@type WeDebug
we.debug = WeDebug

---@type WePhysics
we.physics = WePhysics

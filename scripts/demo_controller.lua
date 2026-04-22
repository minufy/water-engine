return function()
    local self = {
        speed = 220,
        pulse = 0
    }

    function self:start()
        we.debug.log("demo_controller started")
    end

    function self:update(dt)
        if we.input.pressed("a") then
            self.transform.position.x = self.transform.position.x - self.speed * dt
        end
        if we.input.pressed("d") then
            self.transform.position.x = self.transform.position.x + self.speed * dt
        end
        if we.input.pressed("w") then
            self.transform.position.y = self.transform.position.y - self.speed * dt
        end
        if we.input.pressed("s") then
            self.transform.position.y = self.transform.position.y + self.speed * dt
        end

        self.pulse = self.pulse + dt

        local collider = self:GetComponent("Collider")
        local hits = we.physics.query_overlaps(collider)
        for _, hit in ipairs(hits) do
            we.debug.log("Hit " .. hit.name)
        end
    end

    function self:draw()
        local cx = self.transform.position.x + 36
        local cy = self.transform.position.y + 36
        local radius = 12 + math.sin(self.pulse * 4) * 4
        we.graphics.draw_circle(cx, cy, radius, "#e2e8f0", 0)
        we.graphics.draw_rect(self.transform.position.x - 6, self.transform.position.y - 6, 84, 84, "#ffffff", 1)
    end

    return self
end

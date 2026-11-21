-- BENCH SERVEUR DÉDIÉ givre_noir : LOCAL UNIQUEMENT (installé puis retiré par tools/bench_server.ps1).
-- 100 bots joueurs qui se battent (2 équipes) + PNJ ajoutés par paliers (0, 100, 200, 300), 60 s de mesure par palier.
-- Écrit data/givre_noir_srvbench/bench_server_dedie.txt puis done.txt.
include("givre_noir_srvbench/spots.lua")
local DIR = "givre_noir_srvbench"
local NBOTS = 1          -- test des staffs : 1 joueur + 600 PNJ
local STEPS = { 0, 200, 400, 600 }
local WINDOW = 60
local NPC_CLASS = "npc_combine_s"
file.CreateDir(DIR)
local lines = {}
local function L(s)
    lines[#lines + 1] = s
    file.Write(DIR .. "/bench_server_dedie.txt", table.concat(lines, "\n") .. "\n")
    print("[srvbench] " .. s)
end

local function stats(t)
    local n = #t
    if n == 0 then return 0, 0, 0 end
    local s, mx, sorted = 0, 0, {}
    for i, v in ipairs(t) do s = s + v; mx = math.max(mx, v); sorted[i] = v end
    table.sort(sorted)
    return s / n, sorted[math.max(1, math.floor(n * 0.99))], mx
end

-- ---------- mesure ----------
local win
hook.Add("Tick", "gnsb_tick", function()
    if not win then return end
    local now = SysTime()
    win.gap[#win.gap + 1] = (now - win.last) * 1000
    win.last = now
    local ok, ft = pcall(engine.ServerFrameTime)
    if ok and ft then win.ft[#win.ft + 1] = ft * 1000 end
end)
local function startWin(name)
    win = { name = name, t0 = SysTime(), tick0 = engine.TickCount(), ft = {}, gap = {}, last = SysTime() }
    file.Append(DIR .. "/fenetres.txt", "DEBUT " .. name .. " " .. os.time() .. "\n")   -- pour la mesure CPU externe
end
local function endWin()
    local w = win; win = nil
    file.Append(DIR .. "/fenetres.txt", "FIN " .. w.name .. " " .. os.time() .. "\n")
    local el = SysTime() - w.t0
    local ticks = engine.TickCount() - w.tick0
    local expected = el / engine.TickInterval()
    local a, p99, mx = stats(w.ft)
    local ga, gp99, gmx = stats(w.gap)
    local npcs = #ents.FindByClass(NPC_CLASS)
    L(string.format("%-14s frame_srv moy=%.2f p99=%.2f max=%.2f ms | intervalle tick moy=%.2f p99=%.2f max=%.2f ms | ticks %d/%d (rates %d) | joueurs %d PNJ %d | ents %d edicts %d",
        w.name, a, p99, mx, ga, gp99, gmx, ticks, math.floor(expected + 0.5), math.max(0, math.floor(expected - ticks + 0.5)),
        #player.GetAll(), npcs, #ents.GetAll(), ents.GetEdictCount()))
end

-- ---------- bots joueurs (mêmes règles que le bench client) ----------
local MODELS = { "models/player/combine_soldier.mdl", "models/player/police.mdl" }
hook.Add("PlayerSpawn", "gnsb_spawn", function(ply)
    if not ply:IsBot() then return end
    timer.Simple(0, function()
        if not IsValid(ply) then return end
        ply:SetModel(MODELS[(ply:EntIndex() % 2) + 1])
        ply:Give("weapon_smg1"); ply:GiveAmmo(9999, "SMG1", true)
        ply:GodEnable()
        ply.gnsb_team = ply:EntIndex() % 2
        local p = GN_NPC_SPOTS[math.random(#GN_NPC_SPOTS)]
        ply:SetPos(p + Vector(0, 0, 4))
    end)
end)
local function enemyOf(ply)
    local best, bd = nil, 2500 * 2500
    for _, o in ipairs(player.GetBots()) do
        if o ~= ply and o.gnsb_team ~= nil and o.gnsb_team ~= ply.gnsb_team then
            local d = o:GetPos():DistToSqr(ply:GetPos())
            if d < bd then
                local tr = util.TraceLine({ start = ply:EyePos(), endpos = o:EyePos() - Vector(0, 0, 16), filter = { ply, o }, mask = MASK_SHOT })
                if not tr.Hit then best, bd = o, d end
            end
        end
    end
    return best
end
hook.Add("StartCommand", "gnsb_move", function(ply, cmd)
    if not ply:IsBot() then return end
    if CurTime() > (ply.gnsb_scan or 0) then ply.gnsb_t = enemyOf(ply); ply.gnsb_scan = CurTime() + 0.5 end
    if CurTime() > (ply.gnsb_next or 0) then ply.gnsb_yaw = (ply.gnsb_yaw or 0) + math.random(-120, 120); ply.gnsb_next = CurTime() + math.Rand(1.5, 4) end
    cmd:ClearMovement(); cmd:ClearButtons()
    local t = ply.gnsb_t
    if IsValid(t) and t:Alive() then
        cmd:SetViewAngles((t:EyePos() - Vector(0, 0, 20) - ply:EyePos()):Angle())
        cmd:SetSideMove(math.sin(CurTime() * 2 + ply:EntIndex()) * 200)
        local w = ply:GetActiveWeapon()
        if IsValid(w) and w:Clip1() == 0 then cmd:SetButtons(IN_RELOAD)
        elseif (CurTime() + ply:EntIndex() * 0.37) % 1.6 < 1.0 then cmd:SetButtons(IN_ATTACK) end
    else
        cmd:SetViewAngles(Angle(0, ply.gnsb_yaw or 0, 0)); cmd:SetForwardMove(200)
    end
end)

-- ---------- PNJ ----------
local spawned = 0
local function addNPCs(n)
    for i = 1, n do
        local p = GN_NPC_SPOTS[(spawned % #GN_NPC_SPOTS) + 1]
        spawned = spawned + 1
        local e = ents.Create(NPC_CLASS)
        if IsValid(e) then
            e:SetPos(p + Vector(math.random(-24, 24), math.random(-24, 24), 8))
            e:SetKeyValue("additionalequipment", "weapon_smg1")
            e:Spawn()
            e:Activate()
        end
    end
end

-- ---------- déroulé ----------
timer.Simple(25, function()
    L(string.format("BENCH SERVEUR DÉDIÉ givre_noir %s | tickrate %.1f | maxplayers %d | positions PNJ %d", os.date("%Y-%m-%d %H:%M"),
        1 / engine.TickInterval(), game.MaxPlayers(), #GN_NPC_SPOTS))
    local made = 0
    timer.Create("gnsb_bots", 0.1, NBOTS, function() made = made + 1; player.CreateNextBot("srv_" .. made) end)
    timer.Simple(NBOTS * 0.1 + 10, function()
        startWin("vide_100bots")
        local i = 0
        local function step()
            endWin()
            i = i + 1
            if not STEPS[i + 1] then
                file.Write(DIR .. "/done.txt", "ok")
                return
            end
            addNPCs(STEPS[i + 1] - STEPS[i])
            timer.Simple(8, function()                -- laisse les PNJ s'installer
                startWin("100bots+" .. STEPS[i + 1] .. "PNJ")
                timer.Simple(WINDOW, step)
            end)
        end
        timer.Simple(WINDOW, step)
    end)
end)

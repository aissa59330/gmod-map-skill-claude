-- Addon de BENCH givre_noir : DEV LOCAL UNIQUEMENT (installé puis retiré par tools/bench.ps1), jamais sur le serveur.
-- 1) crée 89 bots (moitié droïdes B1, moitié soldats), qui se déplacent en continu ;
-- 2) phase « répartis » : bots dispersés sur tous les repères de spawn, mesure serveur 30 s ;
-- 3) pour chaque point de test : les 89 bots sont regroupés autour du point (pire cas : 90 joueurs à l'écran),
--    le joueur hôte y est téléporté, mesure client (FPS moyen, minimum, 1 % bas) et serveur pendant 5 s ;
-- 4) écrit data/givre_noir_bench/bench_server.txt et bench_client.txt, puis done.txt.
if SERVER then
    AddCSLuaFile()
    AddCSLuaFile("givre_noir_bench/points.lua")
end
include("givre_noir_bench/points.lua")

local DIR = "givre_noir_bench"
local NBOTS = 89
local MEASURE = 5
local SETTLE = 2
local MODELS = { "models/tfa/comm/gg/pm_sw_droid_b1.mdl", "models/player/combine_soldier.mdl" }

local function stats(t)
    local n = #t
    if n == 0 then return 0, 0, 0 end
    local s, mx = 0, 0
    local sorted = {}
    for i, v in ipairs(t) do s = s + v; mx = math.max(mx, v); sorted[i] = v end
    table.sort(sorted)
    return s / n, sorted[math.max(1, math.floor(n * 0.99))], mx
end

if SERVER then
    util.AddNetworkString("gnb_measure")
    file.CreateDir(DIR)
    local lines = {}
    local function L(s)
        lines[#lines + 1] = s
        file.Write(DIR .. "/bench_server.txt", table.concat(lines, "\n") .. "\n")
    end

    -- ---------- mesure serveur ----------
    local win
    local function startWin(name)
        win = { name = name, t0 = SysTime(), tick0 = engine.TickCount(), ft = {}, gap = {}, last = SysTime() }
    end
    hook.Add("Tick", "gnb_tick", function()
        if not win then return end
        local now = SysTime()
        win.gap[#win.gap + 1] = (now - win.last) * 1000      -- intervalle réel entre deux ticks
        win.last = now
        local ok, ft = pcall(engine.ServerFrameTime)          -- temps CPU de la dernière frame serveur
        if ok and ft then win.ft[#win.ft + 1] = ft * 1000 end
    end)
    local function endWin(extra)
        local w = win
        win = nil
        if not w then return end
        local el = SysTime() - w.t0
        local ticks = engine.TickCount() - w.tick0
        local expected = el / engine.TickInterval()
        local missed = math.max(0, math.floor(expected - ticks + 0.5))
        local a, p99, mx = stats(w.ft)
        local ga, gp99, gmx = stats(w.gap)
        local nb = 0
        for _, p in ipairs(player.GetAll()) do if p:IsBot() then nb = nb + 1 end end
        L(string.format("%-20s frame_srv moy=%.2f p99=%.2f max=%.2f ms | tick moy=%.2f p99=%.2f max=%.2f ms | ticks %d/%d (rates %d) | ents %d edicts %d bots %d %s",
            w.name, a, p99, mx, ga, gp99, gmx, ticks, math.floor(expected + 0.5), missed, #ents.GetAll(), ents.GetEdictCount(), nb, extra or ""))
    end

    -- ---------- bots ----------
    local spots = {}
    local function collectSpots()
        for _, e in ipairs(ents.FindByClass("info_target")) do
            local n = e:GetName()
            if string.StartWith(n, "gn_def_spawn_") or string.StartWith(n, "gn_atk_respawn_") then spots[#spots + 1] = e:GetPos() end
        end
        -- (pas les 100 info_player_start : ils sont tous sur la plateforme du spawn et fausseraient la mesure « seul »)
    end
    local HMIN, HMAX = Vector(-16, -16, 0), Vector(16, 16, 72)
    local function free(pos)
        local tr = util.TraceHull({ start = pos, endpos = pos, mins = HMIN, maxs = HMAX, mask = MASK_PLAYERSOLID })
        return not tr.Hit and not tr.StartSolid
    end
    local function ground(pos)
        local tr = util.TraceLine({ start = pos + Vector(0, 0, 40), endpos = pos - Vector(0, 0, 400), mask = MASK_PLAYERSOLID })
        if tr.Hit and not tr.StartSolid then return tr.HitPos + Vector(0, 0, 2) end
    end
    local function place(bot, pos)
        bot:SetPos(pos)
        bot:SetVelocity(-bot:GetVelocity())
        bot.gnb_yaw = math.random(0, 359)
    end
    local function spread(center, bots)
        -- un repère par groupe : on répartit les bots en petite grille autour de chaque repère,
        -- en évitant tout repère à moins de 4000 u du point mesuré (mesure « map seule »)
        bots = bots or player.GetBots()
        local list = {}
        for _, sp in ipairs(spots) do
            if not center or sp:DistToSqr(center) > 4000 * 4000 then list[#list + 1] = sp end
        end
        if #list == 0 then list = spots end
        local n = #list
        for i, b in ipairs(bots) do
            local base = list[(i - 1) % n + 1]
            local k = math.floor((i - 1) / n)
            local p = base + Vector(((k % 3) - 1) * 72, (math.floor(k / 3) - 1) * 72, 4)
            place(b, free(p) and p or base + Vector(0, 0, 4))
        end
    end
    local function edictHistogram()
        local h = {}
        for _, e in ipairs(ents.GetAll()) do
            if e:EntIndex() > 0 then local c = e:GetClass(); h[c] = (h[c] or 0) + 1 end
        end
        local t = {}
        for c, n in pairs(h) do t[#t + 1] = { c, n } end
        table.sort(t, function(a, b) return a[2] > b[2] end)
        local parts = {}
        for i = 1, math.min(25, #t) do parts[#parts + 1] = t[i][1] .. "=" .. t[i][2] end
        L("EDICTS par classe : " .. table.concat(parts, ", "))
    end
    local function gather(center)
        -- anneaux autour du point : positions libres, au sol, pas plus de 120 u de dénivelé
        local bots = player.GetBots()
        local k = 1
        for r = 120, 1400, 80 do
            local n = math.floor(2 * math.pi * r / 70)
            for j = 1, n do
                if k > #bots then return end
                local a = (j / n) * math.pi * 2
                local g = ground(center + Vector(math.cos(a) * r, math.sin(a) * r, 0))
                if g and math.abs(g.z - center.z) < 160 and free(g) then
                    place(bots[k], g)
                    k = k + 1
                end
            end
        end
        local rest = {}
        for i = k, #bots do rest[#rest + 1] = bots[i] end
        if #rest > 0 then spread(center, rest) end        -- pas de place : garés loin (jamais empilés)
        return k - 1
    end

    hook.Add("PlayerSpawn", "gnb_spawn", function(ply)
        if not ply:IsBot() then return end
        timer.Simple(0, function()
            if not IsValid(ply) then return end
            ply:SetModel(MODELS[(ply:EntIndex() % 2) + 1])
            ply:Give("weapon_smg1")
            ply:GiveAmmo(9999, "SMG1", true)
            ply:GodEnable()          -- invincibles : le nombre de joueurs autour du point reste constant pendant la mesure
            ply.gnb_team = ply:EntIndex() % 2   -- équipe 0 = droïdes, 1 = soldats
        end)
    end)
    hook.Add("PlayerDeath", "gnb_death", function(ply)
        if ply:IsBot() then timer.Simple(1, function() if IsValid(ply) then ply:Spawn() end end) end
    end)
    -- combat : chaque bot vise l'ennemi visible le plus proche (recherche toutes les 0,5 s) et tire en rafales
    local function findEnemy(ply)
        local eye = ply:EyePos()
        local best, bd = nil, 2500 * 2500
        for _, o in ipairs(player.GetBots()) do
            if o ~= ply and o.gnb_team ~= nil and o.gnb_team ~= ply.gnb_team then
                local d = o:GetPos():DistToSqr(ply:GetPos())
                if d < bd then
                    local tr = util.TraceLine({ start = eye, endpos = o:EyePos() - Vector(0, 0, 16), filter = { ply, o }, mask = MASK_SHOT })
                    if not tr.Hit then best, bd = o, d end
                end
            end
        end
        return best
    end
    hook.Add("StartCommand", "gnb_move", function(ply, cmd)
        if not ply:IsBot() then return end
        ply.gnb_next = ply.gnb_next or 0
        if CurTime() > ply.gnb_next then
            ply.gnb_yaw = (ply.gnb_yaw or 0) + math.random(-120, 120)
            ply.gnb_next = CurTime() + math.Rand(1.5, 4)
        end
        if CurTime() > (ply.gnb_scan or 0) then
            ply.gnb_target = findEnemy(ply)
            ply.gnb_scan = CurTime() + 0.5
        end
        cmd:ClearMovement()
        cmd:ClearButtons()
        local t = ply.gnb_target
        if IsValid(t) and t:Alive() then
            local ang = (t:EyePos() - Vector(0, 0, 20) - ply:EyePos()):Angle()
            ang.p = ang.p + math.Rand(-3, 3); ang.y = ang.y + math.Rand(-3, 3)    -- dispersion
            cmd:SetViewAngles(ang)
            cmd:SetSideMove(math.sin(CurTime() * 2 + ply:EntIndex()) * 200)      -- straf en combattant
            local burst = (CurTime() + ply:EntIndex() * 0.37) % 1.6 < 1.0      -- rafales de 1 s
            local w = ply:GetActiveWeapon()
            if IsValid(w) and w:Clip1() == 0 then
                cmd:SetButtons(IN_RELOAD)
            elseif burst then
                cmd:SetButtons(IN_ATTACK)
            end
        else
            cmd:SetViewAngles(Angle(0, ply.gnb_yaw or 0, 0))
            cmd:SetForwardMove(200)
            if math.random() < 0.01 then cmd:SetButtons(IN_JUMP) end
        end
    end)

    -- ---------- déroulé ----------
    local started = false
    hook.Add("PlayerInitialSpawn", "gnb_host", function(host)
        if host:IsBot() or started then return end
        started = true
        timer.Simple(8, function()
            collectSpots()
            L(string.format("BENCH givre_noir %s | tickrate %.1f | maxplayers %d | repères %d", os.date("%Y-%m-%d %H:%M"),
                1 / engine.TickInterval(), game.MaxPlayers(), #spots))
            local made = 0
            timer.Create("gnb_bots", 0.15, NBOTS, function()
                made = made + 1
                player.CreateNextBot("bench_" .. made)
            end)
            timer.Simple(NBOTS * 0.15 + 6, function()
                host:GodEnable()
                host:SetMoveType(MOVETYPE_NOCLIP)
                host:SetPos(spots[1] + Vector(0, 0, 64))
                spread()
                timer.Simple(5, function()
                    edictHistogram()
                    startWin("REPARTIS_30s")
                    timer.Simple(30, function()
                        endWin("(bots dispersés sur les repères)")
                        local i = 0
                        local function nextPoint()
                            i = i + 1
                            local p = GN_TOUR[i]
                            if not p then
                                file.Write(DIR .. "/done.txt", "ok")
                                return
                            end
                            -- 1) map seule (bots garés à plus de 4000 u), 2) 89 bots regroupés autour du point
                            spread(p.pos)
                            host:SetMoveType(MOVETYPE_NOCLIP)
                            host:SetPos(p.pos)
                            host:SetEyeAngles(p.ang)
                            timer.Simple(SETTLE, function()
                                startWin(p.name .. "_seul")
                                net.Start("gnb_measure") net.WriteString(p.name .. "_seul") net.WriteFloat(MEASURE) net.Send(host)
                                timer.Simple(MEASURE, function()
                                    endWin("")
                                    gather(p.pos)
                                    host:SetPos(p.pos)
                                    host:SetEyeAngles(p.ang)
                                    timer.Simple(SETTLE, function()
                                        startWin(p.name)
                                        net.Start("gnb_measure") net.WriteString(p.name) net.WriteFloat(MEASURE) net.Send(host)
                                        timer.Simple(MEASURE, function()
                                            endWin("")
                                            timer.Simple(0.5, nextPoint)
                                        end)
                                    end)
                                end)
                            end)
                        end
                        nextPoint()
                    end)
                end)
            end)
        end)
    end)
else
    -- ---------- mesure client ----------
    local cl = {}
    local function W(s)
        cl[#cl + 1] = s
        file.Write("givre_noir_bench/bench_client.txt", table.concat(cl, "\n") .. "\n")
    end
    W(string.format("BENCH client %s | %dx%d | mat_queue_mode %s", os.date("%Y-%m-%d %H:%M"), ScrW(), ScrH(),
        GetConVar("mat_queue_mode"):GetString()))
    local cur
    hook.Add("Think", "gnb_cl", function()
        if not cur then return end
        local ft = FrameTime()
        if ft > 0 then cur.ft[#cur.ft + 1] = ft end
        if SysTime() >= cur.t1 then
            local c = cur
            cur = nil
            local n = #c.ft
            local sum = 0
            local worst = 0
            local sorted = {}
            for i, v in ipairs(c.ft) do sum = sum + v; worst = math.max(worst, v); sorted[i] = v end
            table.sort(sorted, function(a, b) return a > b end)
            local k = math.max(1, math.floor(n * 0.01))
            local low = 0
            for i = 1, k do low = low + sorted[i] end
            low = low / k
            local near = 0
            for _, p in ipairs(player.GetAll()) do
                if p ~= LocalPlayer() and p:GetPos():DistToSqr(LocalPlayer():GetPos()) < 2000 * 2000 then near = near + 1 end
            end
            W(string.format("%-20s fps_moy=%6.1f fps_min=%6.1f fps_1%%bas=%6.1f images=%d joueurs<2000u=%d",
                c.name, n / (SysTime() - c.t0), worst > 0 and 1 / worst or 0, low > 0 and 1 / low or 0, n, near))
        end
    end)
    net.Receive("gnb_measure", function()
        local name = net.ReadString()
        local dur = net.ReadFloat()
        cur = { name = name, t0 = SysTime(), t1 = SysTime() + dur, ft = {} }
    end)
end

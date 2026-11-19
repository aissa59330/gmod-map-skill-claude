-- ADDON DE DEV UNIQUEMENT (tournée caméra + test logique). Ne jamais installer sur le serveur.
if game.GetMap() ~= "givre_noir" then return end

AddCSLuaFile()
AddCSLuaFile("givre_noir_devtour/points.lua")
include("givre_noir_devtour/points.lua")
if file.Exists("givre_noir_devtour/mode.lua", "LUA") then include("givre_noir_devtour/mode.lua") end
GN_MODE = GN_MODE or "complet"     -- "vues" : captures seules (pas de fil de fer, de test logique ni de marche)

local DIR = "givre_noir_shots"

if SERVER then
    util.AddNetworkString("gn_tour_shot")
    util.AddNetworkString("gn_tour_log")

    local logLines = {}
    local function L(s) logLines[#logLines + 1] = s print("[gn_tour] " .. s) end
    local function flush(name)
        file.CreateDir(DIR)
        file.Write(DIR .. "/" .. name, table.concat(logLines, "\n") .. "\n")
    end

    -- relais déclenchés
    local fired = {}
    hook.Add("AcceptInput", "gn_tour_watch", function(ent, input)
        local n = ent:GetName()
        if n ~= "" and string.StartWith(n, "gn_") then fired[n .. ":" .. input] = (fired[n .. ":" .. input] or 0) + 1 end
    end)

    local function byName(n) return ents.FindByName(n)[1] end
    local function hullFree(pos)
        local tr = util.TraceHull({ start = pos + Vector(0, 0, 2), endpos = pos + Vector(0, 0, 2),
            mins = Vector(-16, -16, 0), maxs = Vector(16, 16, 72), mask = MASK_PLAYERSOLID,
            filter = player.GetAll() })   -- ne pas se compter soi-même
        return not tr.StartSolid
    end

    local function checkSpawns()
        local bad, total = 0, 0
        for _, cls in ipairs({ "info_player_start", "info_target" }) do
            for _, e in ipairs(ents.FindByClass(cls)) do
                local n = e:GetName()
                if cls == "info_player_start" or string.StartWith(n, "gn_def_spawn_") or string.StartWith(n, "gn_atk_respawn_") then
                    total = total + 1
                    if not hullFree(e:GetPos()) then bad = bad + 1 L("SPAWN BLOQUE " .. cls .. " " .. n .. " " .. tostring(e:GetPos())) end
                end
            end
        end
        L(string.format("SPAWNS total=%d bloques=%d", total, bad))
    end

    -- test de la chaîne logique : chaque étape = {description, action, vérification, délai}
    local function doorMoved(name, base)
        local e = byName(name) if not IsValid(e) or not base[name] then return false end
        return (e:GetPos() - base[name]):Length() > 8
    end

    -- ===== test porte par porte : fermer tout, puis ouvrir tout, mesurer chaque déplacement =====
    local function runDoorTest(cb)
        local list = {}
        for _, e in ipairs(ents.GetAll()) do
            local c, n = e:GetClass(), e:GetName()
            if (c == "func_door" or c == "func_movelinear") and n ~= "" and not string.StartWith(n, "gn_press_") then
                list[#list + 1] = e
            end
        end
        for _, e in ipairs(list) do e:Fire("Unlock") e:Fire("Close") end
        timer.Simple(6, function()
            local closed = {}
            for _, e in ipairs(list) do if IsValid(e) then closed[e] = e:GetPos() end end
            for _, e in ipairs(list) do e:Fire("Open") end
            timer.Simple(6, function()
                local ok, bad = 0, 0
                for _, e in ipairs(list) do
                    if IsValid(e) then
                        local d = (e:GetPos() - closed[e]):Length()
                        if d > 8 then ok = ok + 1 else
                            bad = bad + 1
                            L(string.format("PORTE KO %s (%s) deplacement=%.0f pos=%s", e:GetName(), e:GetClass(), d, tostring(e:GetPos())))
                        end
                    end
                end
                L(string.format("PORTES testees=%d ok=%d ko=%d", #list, ok, bad))
                -- pour la marche : portes ouvertes, ponts mobiles remis en place
                for _, e in ipairs(list) do if e:GetClass() == "func_movelinear" then e:Fire("Close") end end
                timer.Simple(6, cb)
            end)
        end)
    end

    -- ===== marche pilotée : le joueur suit le tracé à pied (aucun téléport, sauf reprise après échec) =====
    local function runWalk(ply, route, label, cb)
        local i, fails, bestD, lastProg, t0 = 1, 0, math.huge, CurTime(), CurTime()
        ply:SetMoveType(MOVETYPE_WALK)
        ply:SetPos(route[1].pos + Vector(0, 0, 4))
        ply:SetRunSpeed(400) ply:SetWalkSpeed(250)
        hook.Add("StartCommand", "gn_walk", function(p, cmd)
            if p ~= ply then return end
            local wp = route[i]
            if not wp then return end
            local pos = p:GetPos()
            local d = wp.pos - pos
            local dz = d.z
            d.z = 0
            local dist = d:Length()
            if dist < 40 and math.abs(dz) < 72 then
                i = i + 1
                bestD, lastProg = math.huge, CurTime()
                if not route[i] then
                    hook.Remove("StartCommand", "gn_walk")
                    L(string.format("MARCHE %s FIN : %d points, %d echec(s), %.0f s", label, #route, fails, CurTime() - t0))
                    timer.Simple(0.5, cb)
                end
                return
            end
            if dist < bestD - 8 then bestD, lastProg = dist, CurTime() end
            local stuck = CurTime() - lastProg
            if stuck > 8 then
                fails = fails + 1
                L(string.format("MARCHE %s ECHEC vers %s (reste %.0f u, dz=%.0f) bloque a %s", label, wp.name, dist, dz, tostring(pos)))
                p:SetPos(wp.pos + Vector(0, 0, 4))      -- reprise du test au point suivant
                bestD, lastProg = math.huge, CurTime()
                return
            end
            local ang = d:Angle()
            cmd:ClearMovement() cmd:ClearButtons()
            cmd:SetViewAngles(ang)
            cmd:SetForwardMove(400)
            cmd:SetButtons(IN_FORWARD + IN_SPEED + (stuck > 2.5 and IN_JUMP or 0))
        end)
    end

    local function runLogic(ply)
        local base = {}
        for _, e in ipairs(ents.GetAll()) do
            local n = e:GetName()
            if n ~= "" then base[n] = e:GetPos() end
        end
        local function tp(v) ply:SetMoveType(MOVETYPE_WALK) ply:SetPos(v) end
        local function press(n) local e = byName(n) if IsValid(e) then e:Fire("Unlock") e:Fire("Press") end end
        local function moved(...)
            local all = true
            for _, n in ipairs({ ... }) do
                local e = byName(n)
                local d = (IsValid(e) and base[n]) and (e:GetPos() - base[n]) or nil
                if not doorMoved(n, base) then
                    all = false
                    L(string.format("  PORTE IMMOBILE %s valide=%s depl=%s", n, tostring(IsValid(e)), d and tostring(d) or "?"))
                end
            end
            return all
        end
        -- aucun son du piratage ne doit être actif avant le hack
        for _, n in ipairs({ "gn_dc_voice", "gn_dc_voice_fin", "gn_dc_siren" }) do
            for _, e in ipairs(ents.FindByName(n)) do
                L(string.format("SON %s actif=%s", n, tostring(e:GetInternalVariable("m_fActive"))))
            end
        end
        -- vrai maintien de [E] : le joueur se place devant la molette, la regarde et garde [E] enfoncée
        local useUntil, useAng = 0, nil
        hook.Add("StartCommand", "gn_force_use", function(p, cmd)
            if p:IsBot() or CurTime() >= useUntil then return end
            cmd:SetButtons(bit.bor(cmd:GetButtons(), IN_USE))
            if useAng then cmd:SetViewAngles(useAng) end
        end)
        local function hold(n, secs)
            local e = byName(n)
            if not IsValid(e) then return end
            e:Fire("Unlock")
            local p = player.GetAll()[1]
            local c = e:WorldSpaceCenter()
            local pos = Vector(c.x - 40, c.y, c.z - 50)          -- yeux 14 u au-dessus de la molette, 40 u devant
            p:SetMoveType(MOVETYPE_NOCLIP)
            p:SetPos(pos)
            useAng = (c - (pos + Vector(0, 0, 64))):Angle()
            p:SetEyeAngles(useAng)
            useUntil = CurTime() + secs + 1
        end
        local steps = {
            { "phase 1 (auto au chargement)", function() end, 1, function() return fired["gn_phase_1_start:Trigger"] end },
            { "entree hangar", function() tp(Vector(-9400, 0, 8)) end, 2, function() return fired["gn_phase_2_start:Trigger"] end },
            { "AA detruites", function() for i = 1, 3 do byName("aa_" .. i):Fire("Break") end end, 6,
              function() return fired["gn_phase_2_done:Trigger"] and moved("gn_door_gate", "gn_door_conduit") end },
            { "arrivee usine", function() tp(Vector(1536, -1000, 8)) end, 2, function() return fired["gn_phase_4_start:Trigger"] end },
            { "generateurs", function() for i = 1, 3 do press("gn_gen_" .. i) end end, 5,
              function() return fired["gn_phase_4_done:Trigger"] and fired["gn_factory_light_east:TurnOff"] and moved("gn_sas_door_1", "gn_door_4n", "gn_door_4s") end },
            { "cycle sas 1", function() tp(Vector(4096, 0, 8)) end, 32,
              function() return fired["gn_sas_door1_closed:Trigger"] and moved("gn_sas_door_2") end },
            { "armurerie garnison", function() for i = 1, 3 do press("gn_armory_" .. i) end end, 5,
              function() return fired["gn_phase_5_done:Trigger"] and moved("gn_door_5a", "gn_door_5n", "gn_door_5s", "gn_dc_door_1") end },
            { "hack etape 1", function() press("gn_hack_button_1") end, 2, function() return fired["gn_hack_timer_1:Enable"] and fired["gn_dc_lock_timer:Enable"] end },
            { "verrouillage aleatoire", function() byName("gn_dc_lock_timer"):Fire("FireTimer") end, 3,
              function() return fired["gn_dc_case:PickRandom"] and fired["gn_sentinel_dc_lock:Trigger"] end },
            { "hack etapes 2-3", function()
                byName("gn_hack_timer_1"):Fire("FireTimer")
                timer.Simple(1, function() byName("gn_hack_button_2"):Fire("Press") end)
                timer.Simple(2, function() byName("gn_hack_timer_2"):Fire("FireTimer") end)
                timer.Simple(3, function() byName("gn_hack_button_3"):Fire("Press") end)
                timer.Simple(4, function() byName("gn_hack_timer_3"):Fire("FireTimer") end)
              end, 9,
              function() return fired["gn_hack_button_2:Unlock"] and fired["gn_hack_button_3:Unlock"] and fired["gn_phase_6_done:Trigger"]
                  and moved("gn_door_6w", "gn_door_6a", "gn_door_6b", "gn_door_6e") end },
            { "cellules prison", function() for i = 1, 3 do press("gn_cellblock_" .. i) end end, 5,
              function() return fired["gn_phase_7_done:Trigger"] and moved("gn_cell_a_1", "gn_cell_b_1", "gn_cell_c_1", "gn_sas2_door_1", "gn_door_7n", "gn_door_7s") end },
            { "cycle sas 2", function() tp(Vector(9216, -5120, 772)) end, 32,
              function() return fired["gn_sas2_door1_closed:Trigger"] and moved("gn_sas2_door_2") end },
            { "charges antenne", function() for i = 1, 3 do press("gn_charge_" .. i) end end, 5,
              function() return fired["gn_phase_8_done:Trigger"] and moved("gn_door_8a", "gn_door_8n", "gn_door_8s") end },
            { "reacteur", function() for i = 1, 3 do press("gn_reactor_" .. i) end end, 5,
              function() return fired["gn_phase_9_done:Trigger"] and fired["gn_phase_10_start:Trigger"]
                  and moved("gn_exfil_door_0", "gn_exfil_door_1", "gn_exfil_door_3", "gn_exfil_door_5") end },
            { "pont retractable", function() byName("gn_sentinel_core_bridge"):Fire("Trigger") end, 6, function() return moved("gn_core_bridge_1") end },
            { "scellement puits 1", function() tp(Vector(-2430, -5890, 3844)) end, 16,
              function() return fired["gn_sentinel_exfil_seal:Trigger"] and fired["gn_exfil_door_0:Close"] end },
            { "arrivee glacier", function() tp(Vector(-8700, -5888, 6916)) end, 2,
              function() return fired["gn_phase_10_done:Trigger"] and fired["gn_phase_11_start:Trigger"] and fired["gn_exfil_clock:CancelPending"] end },
            -- ---- mini-jeux (mécanique seule : chaque action doit déclencher la suite prévue) ----
            { "MJ bouclier AA", function() for k = 1, 2 do local e = byName("gn_shieldgen_" .. k) if IsValid(e) then e:Fire("Break") end end end, 2,
              function() return fired["gn_shield_counter:Add"] == 2 and fired["gn_aa_shield:Disable"] end },
            { "MJ generateur", function()
                for k = 1, 3 do local n = "gn_gen_1_cb_" .. k; local e = byName(n) if IsValid(e) then e:Fire("Unlock") e:Fire("Press") end end
              end, 9,
              function() return fired["gn_gen_1_cbs:Add"] == 3 and fired["gn_gen_1_surcharge:Trigger"] and fired["gn_gen_1:Press"] end },
            { "MJ chaine droides", function() press("gn_chaine_levier") end, 2,
              function() return fired["gn_bonus_chaine:Trigger"] and fired["gn_conveyor_1:SetSpeed"] end },
            { "MJ coupure piratage", function()
                byName("gn_hack_cut"):Fire("Trigger")
                timer.Simple(1, function() press("gn_dc_breaker") end)
              end, 3,
              function() return fired["gn_dc_power_cut:SetValue"] and fired["gn_hack_resume:Trigger"] and fired["gn_hack_tick:Enable"] end },
            { "MJ champ de force", function() for k = 1, 3 do local e = byName("gn_prison_cell_" .. k) if IsValid(e) then e:Fire("Break") end end end, 2,
              function() return fired["gn_prison_cells:Add"] == 3 and fired["gn_prison_field:Disable"] and fired["gn_cellblock_1:Unlock"] end },
            { "MJ charge armer/desamorcer", function()
                hold("gn_charge_1_arm", 8)
                timer.Simple(10, function() hold("gn_charge_1_disarm", 4) end)
              end, 16,
              function() return fired["gn_charge_1_count:Trigger"] and fired["gn_charge_1_disarm:Unlock"] and fired["gn_charge_1_count:CancelPending"] end },
            { "MJ vannes reacteur", function()
                hold("gn_core_valve_1", 5)
                timer.Simple(7, function() hold("gn_core_valve_2", 5) end)
                timer.Simple(14, function() hold("gn_core_valve_3", 5) end)
              end, 22,
              function() return fired["gn_core_window:Trigger"] and fired["gn_core_valves_done:Trigger"] and fired["gn_reactor_1:Unlock"] end },

        }
        local i = 0
        local function nxt()
            i = i + 1
            local s = steps[i]
            if not s then
                for k, _ in SortedPairs(fired) do L("FIRED " .. k) end
                flush("logic.txt")
                timer.Simple(20, function() runDoorTest(function()   -- laisse finir les sorties temporisées du test logique
                    runWalk(ply, GN_WALK, "principale", function()
                        runWalk(ply, GN_WALK_3A, "conduits", function()
                            -- ambiance du piratage : salle dans le noir, alarme rouge, compte à rebours
                            for _, e in ipairs(ents.FindByName("gn_hack_fx_on")) do e:Fire("Trigger") end
                            ply:SetMoveType(MOVETYPE_NOCLIP) ply:SetPos(Vector(11330, -380, 832)) ply:SetEyeAngles(Angle(8, 40, 0))
                            timer.Simple(7, function() net.Start("gn_tour_shot") net.WriteString("z6_alarme_hack") net.Send(ply) end)
                            timer.Simple(9, function() ply:SetPos(Vector(10400, -1300, 832)) ply:SetEyeAngles(Angle(5, 30, 0)) end)
                            timer.Simple(12, function() net.Start("gn_tour_shot") net.WriteString("z6_alarme_dc") net.Send(ply) end)
                            timer.Simple(14, function()
                                for _, e in ipairs(ents.FindByName("gn_hack_fx_off")) do e:Fire("Trigger") end
                                ply:SetPos(Vector(-9400, -7500, 7100)) ply:SetEyeAngles(Angle(10, 135, 0))
                            end)
                            timer.Simple(16.5, function() net.Start("gn_tour_shot") net.WriteString("fin_glacier") net.Send(ply) end)
                            timer.Simple(18, function()
                                L("LOGIC FIN") flush("logic.txt")
                                file.Write(DIR .. "/done.txt", "ok")
                            end)
                        end)
                    end)
                end) end)
                return
            end
            local ok, err = pcall(s[2])
            if not ok then L("LOGIC ERREUR " .. s[1] .. " : " .. tostring(err)) end
            timer.Simple(s[3], function()
                if s[4] then
                    local ok2, res = pcall(s[4])
                    L(string.format("LOGIC %-28s %s", s[1], not ok2 and ("ERREUR " .. tostring(res)) or (res and "OK" or "ECHEC")))
                end
                nxt()
            end)
        end
        nxt()
    end

    local function runTour(ply)
        ply:StripWeapons()
        ply:GodEnable()
        ply:SetMoveType(MOVETYPE_NOCLIP)
        ply:ConCommand("net_graph 1")
        local steps = {}
        for _, p in ipairs(GN_TOUR) do steps[#steps + 1] = { p = p, wire = false } end
        if GN_MODE ~= "vues" then
            for _, p in ipairs(GN_TOUR) do steps[#steps + 1] = { p = p, wire = true } end
        end
        local i = 0
        local function nxt()
            i = i + 1
            local s = steps[i]
            if not s then
                ply:ConCommand("mat_wireframe 0")
                ply:SetMoveType(MOVETYPE_NOCLIP)
                checkSpawns()          -- le joueur est loin des spawns à ce moment
                flush("tour.txt")
                if GN_MODE == "vues" then
                    file.Write(DIR .. "/done.txt", "ok")
                else
                    runLogic(ply)
                end
                return
            end
            if s.wire then ply:ConCommand("mat_wireframe 1") end
            -- le brouillard du canyon ne sert qu'aux zones 1-2 (en event il se coupe à la fin de la phase 2)
            if not string.StartWith(s.p.name, "z1_") and not string.StartWith(s.p.name, "z2_") then
                for _, f in ipairs(ents.FindByName("gn_fog")) do f:Fire("TurnOff") end
            else
                for _, f in ipairs(ents.FindByName("gn_fog")) do f:Fire("TurnOn") end
            end
            ply:SetMoveType(MOVETYPE_NOCLIP)
            ply:SetPos(s.p.pos)
            ply:SetEyeAngles(s.p.ang)
            timer.Simple(0.5, function()
                -- le joueur reste en noclip : il ne doit déclencher aucun trigger pendant la tournée caméra
                local stuck = not hullFree(s.p.pos)
                if not s.wire then L(string.format("POINT %s pos=%s coince=%s", s.p.name, tostring(s.p.pos), tostring(stuck))) end
            end)
            timer.Simple(2.5, function()
                net.Start("gn_tour_shot") net.WriteString(s.p.name .. (s.wire and "_wire" or "")) net.Send(ply)
            end)
            timer.Simple(3.5, nxt)
        end
        nxt()
    end

    hook.Add("PlayerInitialSpawn", "gn_tour_start", function(ply)
        timer.Simple(10, function() if IsValid(ply) then runTour(ply) end end)
    end)
else
    local pending
    local frames = {}
    hook.Add("Think", "gn_tour_fps", function()
        frames[#frames + 1] = RealFrameTime()
        if #frames > 90 then table.remove(frames, 1) end
    end)
    net.Receive("gn_tour_shot", function() pending = net.ReadString() end)
    hook.Add("HUDShouldDraw", "gn_tour_nohud", function(n) if n ~= "CHudGMod" then return false end end)
    hook.Add("PostRender", "gn_tour_capture", function()
        if not pending then return end
        local name = pending
        pending = nil
        local data = render.Capture({ format = "png", x = 0, y = 0, w = ScrW(), h = ScrH(), alpha = false })
        file.CreateDir(DIR)
        if data then file.Write(DIR .. "/" .. name .. ".png", data) end
        local sum = 0
        for _, f in ipairs(frames) do sum = sum + f end
        local fps = #frames > 0 and (#frames / sum) or 0
        file.Append(DIR .. "/fps.txt", string.format("%s %.0f\n", name, fps))
    end)
end

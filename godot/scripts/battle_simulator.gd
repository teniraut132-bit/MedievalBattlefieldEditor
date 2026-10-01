class_name BattleSimulator
extends RefCounted

# Deterministic single-click battle resolution used by the migrating editor.
# Values are percentage-like legacy stats; equipment/weapon fields directly
# contribute to combat power, while training and morale scale effective strength.

var last_result: Dictionary = {}

func _num(unit: Dictionary, key: String, default_value: float = 0.0) -> float:
    return float(unit.get(key, default_value))

func combat_power(unit: Dictionary) -> float:
    var personnel := maxf(1.0, _num(unit, "personnel", 100.0))
    var training := clampf(_num(unit, "training", 50.0), 0.0, 100.0)
    var morale := clampf(_num(unit, "morale", 30.0), 0.0, 100.0)
    var quality := clampf(_num(unit, "quality", 50.0), 0.0, 100.0)
    var weapon := clampf(_num(unit, "weapon_power", quality), 0.0, 100.0)
    var armor := clampf(_num(unit, "armor_power", quality), 0.0, 100.0)
    var troop_bonus := maxf(0.5, _num(unit, "combat_bonus", 1.0))
    var training_factor := 0.55 + training / 125.0
    var morale_factor := 0.45 + morale / 110.0
    var equipment_factor := 0.55 + ((quality + weapon * 0.65 + armor * 0.35) / 200.0)
    return personnel * training_factor * morale_factor * equipment_factor * troop_bonus

func resolve(attacker: Dictionary, defender: Dictionary) -> Dictionary:
    var ap := combat_power(attacker)
    var dp := combat_power(defender)
    var total := maxf(1.0, ap + dp)
    var attacker_share := ap / total
    var defender_share := dp / total

    var a_losses_pct := clampf(18.0 + defender_share * 42.0, 8.0, 68.0)
    var d_losses_pct := clampf(18.0 + attacker_share * 42.0, 8.0, 68.0)
    if ap > dp:
        a_losses_pct *= 0.72
        d_losses_pct *= 1.18
    elif dp > ap:
        a_losses_pct *= 1.18
        d_losses_pct *= 0.72

    var a_old := maxf(0.0, _num(attacker, "personnel", 100.0))
    var d_old := maxf(0.0, _num(defender, "personnel", 100.0))
    var a_casualties := int(round(a_old * a_losses_pct / 100.0))
    var d_casualties := int(round(d_old * d_losses_pct / 100.0))
    var a_remaining := maxf(0.0, a_old - a_casualties)
    var d_remaining := maxf(0.0, d_old - d_casualties)

    var a_morale_delta := -clampf(a_losses_pct * 0.55 + (5.0 if dp > ap else 0.0), 5.0, 60.0)
    var d_morale_delta := -clampf(d_losses_pct * 0.55 + (5.0 if ap > dp else 0.0), 5.0, 60.0)
    var a_training_gain := clampf(a_losses_pct * 0.12, 1.0, 8.0)
    var d_training_gain := clampf(d_losses_pct * 0.12, 1.0, 8.0)

    attacker["personnel"] = a_remaining
    defender["personnel"] = d_remaining
    attacker["morale"] = clampf(_num(attacker, "morale", 30.0) + a_morale_delta, 0.0, 100.0)
    defender["morale"] = clampf(_num(defender, "morale", 30.0) + d_morale_delta, 0.0, 100.0)
    attacker["training"] = clampf(_num(attacker, "training", 50.0) + a_training_gain, 0.0, 100.0)
    defender["training"] = clampf(_num(defender, "training", 50.0) + d_training_gain, 0.0, 100.0)

    # Equipment losses are proportional to casualties and quality, but retained
    # independently from personnel so later battles can use degraded gear.
    attacker["equipment_condition"] = clampf(_num(attacker, "equipment_condition", 100.0) - a_losses_pct * 0.72, 0.0, 100.0)
    defender["equipment_condition"] = clampf(_num(defender, "equipment_condition", 100.0) - d_losses_pct * 0.72, 0.0, 100.0)

    var winner := "draw"
    if ap > dp * 1.03: winner = "attacker"
    elif dp > ap * 1.03: winner = "defender"

    last_result = {
        "winner": winner,
        "attacker_before": a_old,
        "defender_before": d_old,
        "attacker_casualties": a_casualties,
        "defender_casualties": d_casualties,
        "attacker_loss_pct": a_losses_pct,
        "defender_loss_pct": d_losses_pct,
        "attacker_training_gain": a_training_gain,
        "defender_training_gain": d_training_gain,
        "attacker_morale_delta": a_morale_delta,
        "defender_morale_delta": d_morale_delta,
        "attacker_equipment_loss_pct": a_losses_pct * 0.72,
        "defender_equipment_loss_pct": d_losses_pct * 0.72,
        "attacker_power": ap,
        "defender_power": dp,
    }
    return last_result

func format_result(result: Dictionary) -> String:
    var who := str(result.get("winner", "draw"))
    var winner_label := {"attacker":"Атакующий","defender":"Обороняющийся","draw":"Ничья"}.get(who, "Ничья")
    return "Результат: %s\n\nАтакующий: -%d человек (%.1f%%), мораль %+.1f, опыт +%.1f\nОбороняющийся: -%d человек (%.1f%%), мораль %+.1f, опыт +%.1f\n\nПотери снаряжения: %.1f%% / %.1f%%" % [
        winner_label,
        int(result.get("attacker_casualties",0)), float(result.get("attacker_loss_pct",0.0)),
        float(result.get("attacker_morale_delta",0.0)), float(result.get("attacker_training_gain",0.0)),
        int(result.get("defender_casualties",0)), float(result.get("defender_loss_pct",0.0)),
        float(result.get("defender_morale_delta",0.0)), float(result.get("defender_training_gain",0.0)),
        float(result.get("attacker_equipment_loss_pct",0.0)), float(result.get("defender_equipment_loss_pct",0.0))
    ]

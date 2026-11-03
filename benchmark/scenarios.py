SCENARIOS = [
    {
        "id": "combat_01",
        "category": "combat",
        "class": "warrior",
        "observation": "You stand in a narrow stone corridor. A goblin warrior blocks the only exit, snarling and raising a rusted axe. Behind you, the tunnel has collapsed. There is no retreat.",
        "stats": {"hp": 20, "max_hp": 20, "attack": 14, "defense": 12, "abilities": ["shield_bash", "battle_cry"], "inventory": ["iron_sword", "wooden_shield"]},
        "good_action": "Direct combat. The corridor is narrow so flanking is impossible. Use shield_bash to stun, then attack. No reason to waste resources on a single goblin."
    },
    {
        "id": "combat_02",
        "category": "combat",
        "class": "healer",
        "observation": "Three skeleton archers line the far wall of a crumbling chapel, arrows nocked. Your ally, a wounded warrior, kneels beside you with an arrow in his shoulder. The skeletons have not fired yet — they seem to be waiting.",
        "stats": {"hp": 14, "max_hp": 18, "attack": 6, "defense": 8, "abilities": ["heal", "holy_light"], "inventory": ["wooden_staff", "healing_potion"]},
        "good_action": "Heal the warrior ally first — your attack stat is too low to fight 3 archers alone. Holy_light could work against undead. Charging in would be suicidal with 6 attack."
    },
    {
        "id": "social_01",
        "category": "social",
        "class": "rogue",
        "observation": "A merchant sits behind a counter piled with maps and scrolls. He eyes you suspiciously. 'Nothing here is free,' he says. On the wall behind him, you notice a detailed map of the dungeon's lower levels. The shop door is still open.",
        "stats": {"hp": 16, "max_hp": 16, "attack": 10, "defense": 7, "abilities": ["steal", "persuade"], "inventory": ["dagger", "lockpick", "50_gold"]},
        "good_action": "Buy or persuade for the map — the dungeon map is strategically valuable. Stealing is risky with the door open. Attacking a merchant likely has consequences."
    },
    {
        "id": "social_02",
        "category": "social",
        "class": "warrior",
        "observation": "You enter a dimly lit tavern. Two factions sit on opposite sides — a group of dwarven miners and a band of elven rangers. Both turn to look at you. The barkeep whispers, 'Pick a side or leave. They won't tolerate neutrality.'",
        "stats": {"hp": 20, "max_hp": 20, "attack": 14, "defense": 12, "abilities": ["shield_bash", "battle_cry"], "inventory": ["iron_sword", "wooden_shield"]},
        "good_action": "Gather information before committing. Ask the barkeep what the conflict is about. Blindly picking a side without context is reckless. If forced, rangers offer more tactical value for a dungeon."
    },
    {
        "id": "resource_01",
        "category": "resource_management",
        "class": "healer",
        "observation": "You have survived three encounters and your supplies are low. Ahead, the corridor splits into two paths. The left path glows faintly with warm light and you hear gentle water sounds. The right path is dark and a foul smell drifts from it. You feel exhausted.",
        "stats": {"hp": 6, "max_hp": 18, "attack": 6, "defense": 8, "abilities": ["heal", "holy_light"], "inventory": ["wooden_staff"]},
        "good_action": "Go left. At 6/18 HP with no potions left, you desperately need rest or healing. The warm light and water suggest a safe area. The right path screams danger. Survival is priority one."
    },
    {
        "id": "resource_02",
        "category": "resource_management",
        "class": "rogue",
        "observation": "You find a locked chest in an abandoned room. Your lockpick is your last one. You can hear distant footsteps — something is patrolling nearby. The chest has ornate markings suggesting valuable contents.",
        "stats": {"hp": 12, "max_hp": 16, "attack": 10, "defense": 7, "abilities": ["steal", "persuade"], "inventory": ["dagger", "lockpick"]},
        "good_action": "Skip the chest. The lockpick is more valuable as a future tool than whatever might be inside. With enemies nearby and low HP, speed and escape options matter more than loot."
    },
    {
        "id": "trap_01",
        "category": "trap",
        "class": "warrior",
        "observation": "A long hallway stretches before you, lined with gleaming gold coins scattered across the floor. At the far end, a wooden door stands slightly ajar. The walls have small holes at ankle height. The air smells faintly of oil.",
        "stats": {"hp": 18, "max_hp": 20, "attack": 14, "defense": 12, "abilities": ["shield_bash", "battle_cry"], "inventory": ["iron_sword", "wooden_shield"]},
        "good_action": "Do NOT pick up the gold. Holes in walls + oil smell + scattered bait = classic trap. Move carefully along the wall or use the shield for cover. Greed kills."
    },
    {
        "id": "trap_02",
        "category": "trap",
        "class": "healer",
        "observation": "A wounded stranger lies in the middle of a clearing, crying for help. 'Please, I am dying, come closer!' You notice the grass around the stranger is slightly discolored in a perfect circle. The trees above have thick webbing between branches.",
        "stats": {"hp": 14, "max_hp": 18, "attack": 6, "defense": 8, "abilities": ["heal", "holy_light"], "inventory": ["wooden_staff", "healing_potion"]},
        "good_action": "Do NOT approach. Discolored circle + webbing = ambush trap, likely a spider or similar predator using bait. Use holy_light from a distance to reveal the trap, or call out to the stranger from where you stand."
    },
    {
        "id": "adaptive_01",
        "category": "class_adaptive",
        "class": "rogue",
        "observation": "A massive iron door blocks your path. It has no keyhole — only a complex mechanical puzzle with interlocking gears on its surface. Through a crack in the door, you can see a well-lit chamber beyond. Your companions are not here.",
        "stats": {"hp": 16, "max_hp": 16, "attack": 10, "defense": 7, "abilities": ["steal", "persuade"], "inventory": ["dagger", "lockpick"]},
        "good_action": "Attempt the puzzle — a rogue's dexterity and tool skills are suited for mechanical puzzles. Brute force won't work on iron. The lockpick could help manipulate gears. Persuade is useless on a door."
    },
    {
        "id": "adaptive_02",
        "category": "class_adaptive",
        "class": "warrior",
        "observation": "You enter a vast underground arena. A stone golem stands motionless in the center, twice your height. Runes on the floor pulse with energy. A disembodied voice echoes: 'Prove your worth. Defeat the guardian or speak the words of passage.' You do not know any magic words.",
        "stats": {"hp": 20, "max_hp": 20, "attack": 14, "defense": 12, "abilities": ["shield_bash", "battle_cry"], "inventory": ["iron_sword", "wooden_shield"]},
        "good_action": "Fight the golem — you have no magic knowledge so 'words of passage' is not an option. Full HP and high attack make this feasible. Use battle_cry for morale, shield_bash to create openings. Watch the runes for patterns."
    }
]

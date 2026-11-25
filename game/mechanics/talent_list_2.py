"""The own talents of the lines added later (see talent_list.py): Koffing,
Grimer, Dratini, Aerodactyl, Magikarp, Lapras, Gastly, Cubone, Chansey,
Scyther, Kangaskhan, Tauros, Rhyhorn, Exeggcute, Hitmonlee, Hitmonchan,
Mr. Mime, Jynx, Electabuzz, Magmar, Pinsir and Tangela. Their trees reuse
the shared talents (and a few other lines' own) where they fit."""

from .talent_core import _t

_PUNCHES = ("Fire Punch", "Ice Punch", "Thunder Punch")

MORE_TALENTS = [
    # Koffing: smog, smoke and going out with a bang.
    _t("Smog Cloud", "own", "Smog hits every enemy.", ("Smog", {"spread": True})),
    _t("Toxic Smog", "own", "Smog badly poisons: it gets worse every round.", ("Smog", {"toxic": True})),
    _t("Sludge Bomb", "own", "Sludge hits harder: 90 power, and poisons 40% of the time.",
       ("Sludge", {"power": 90, "status_chance": 10})),
    _t("Toxic Storm", "own", "Sludge hits every enemy at full damage.", ("Sludge", {"spread": True})),
    _t("Thick Fog", "own", "At the start of each battle, each enemy's accuracy has a 50% chance to fall 2 stages.",
       lower__accuracy=2),
    _t("Plague Cloud", "own", "At the start of each battle, each enemy has a 60% chance to be poisoned.",
       aura__poison=60),
    _t("Smog Shroud", "own", "While the user stands, the whole party takes 20% less damage.", ancient_roots=0.2),
    _t("Final Flash", "own", "Self-Destruct and Explosion hit harder: 200 and 250 power.",
       ("Self-Destruct", {"power": 200}), ("Explosion", {"power": 250})),
    # Grimer: a body of sludge.
    _t("Sticky Sludge", "own", "Sludge has a 50% chance to lower the target's Speed 1 stage.",
       ("Sludge", {"stages": (("speed", -1),), "stage_chance": 50})),
    _t("Toxic Body", "own", "Whoever hits the user has a 30% chance to be poisoned.", retaliate__poison=30),
    _t("Gunk Feast", "own", "Knocking an enemy out with a Poison move heals the user half its max HP.",
       harvest__poison=0.5),
    _t("Sludge Wave", "own", "Sludge hits every enemy, the others at 60% damage.",
       ("Sludge", {"spread": True, "spread_share": 0.6})),
    _t("Acid Armor", "own", "Harden raises the user's Defense 2 stages more (3 in all).",
       ("Harden", {"stages": (("defense", 2),)})),
    _t("Sludge Fist", "own", "The basic attack becomes a Poison move (with STAB), with a 30% chance to poison.",
       ("basic", {"type": "poison", "status": "poison", "status_chance": 30})),
    _t("Muck Mountain", "own", "The first hit the user takes in each battle deals no damage, and whoever hits "
       "the user has a 30% chance to be poisoned.", sturdy=1.0, retaliate__poison=30),
    _t("Putrid Rot", "own", "Poisoned enemies take 40% more damage from the user.", prey__poison=0.4),
    # Dratini: coils, dragon fury and Dragonite's wings.
    _t("Dragon Coil", "own", "Wrap hits every enemy.", ("Wrap", {"spread": True})),
    _t("Dragon Pulse", "own", "Dragon Rage deals 60 damage (not 40).", ("Dragon Rage", {"fixed_amount": 60})),
    _t("Outrage", "own", "Dragon Rage hits every enemy.", ("Dragon Rage", {"spread": True})),
    _t("Draco Meteor", "own", "Hyper Beam becomes a Dragon move.", ("Hyper Beam", {"type": "dragon"})),
    _t("Dragon Rush", "own", "Each Normal or Dragon move in a row deals 30% more than the last, up to +90%.",
       streak__normal=0.3, streak__dragon=0.3),
    _t("Multiscale", "own", "The first hit the user takes in each battle deals half damage.", sturdy=0.5),
    _t("Dragon Dance", "own", "Agility also raises the user's Attack 1 stage.",
       ("Agility", {"stages": (("attack", 1),)})),
    _t("Dragon Wings", "own", "Wing Attack hits harder: 70 power, and hits every enemy, the others at 50% damage.",
       ("Wing Attack", {"power": 70, "spread": True, "spread_share": 0.5})),
    _t("Sky Sovereign", "own", "Wing Attack and Hyper Beam deal 30% more.",
       ("Wing Attack", {"scale": 0.3}), ("Hyper Beam", {"scale": 0.3})),
    # Aerodactyl: an ancient raptor of the skies.
    _t("Ancient Power", "own", "Rock Slide hits every enemy at full damage.", ("Rock Slide", {"spread": True})),
    _t("Primeval Jaws", "own", "Bite hits much harder: 100 power, making the target flinch 30% of the time.",
       ("Bite", {"power": 100, "flinch": 20})),
    _t("Sky Terror", "own", "Wing Attack hits every enemy at full damage.", ("Wing Attack", {"spread": True})),
    _t("Prehistoric Roar", "own", "At the start of each battle, each enemy's Attack and Speed have a 50% chance "
       "to fall 1 stage.", lower__attack=1, lower__speed=1),
    # Magikarp: it never gives up, and Gyarados's rage.
    _t("Bounce", "own", "Splash raises the user's Attack and Speed 1 stage.",
       ("Splash", {"stages": (("attack", 1), ("speed", 1))})),
    _t("Flail", "own", "Below 1/3 HP, the user's Normal moves deal 2× damage.", pinch__normal=1.0),
    _t("Never Give Up", "own", "Once a battle, ending a round below 1/3 HP heals the user half its max HP, and "
       "Splash heals it 1/4 of its max HP.", ("Splash", {"heal": 0.25}), second_wind=0.5),
    _t("Shining Scales", "own", "The first hit the user takes in each battle deals no damage, and while it "
       "stands the whole party takes 15% less damage.", sturdy=1.0, ancient_roots=0.15),
    _t("Raging Storm", "own", "Each Normal or Water move in a row deals 25% more than the last, up to +75%.",
       streak__normal=0.25, streak__water=0.25),
    _t("Aqua Rage", "own", "Hydro Pump never misses, and hits 20% harder.",
       ("Hydro Pump", {"sure_hit": True, "scale": 0.2})),
    # Lapras: the gentle ferry of the seas.
    _t("Shell Armor", "own", "Super-effective hits on the user deal 30% less damage.", filter=0.3),
    _t("Gentle Ferry", "own", "While the user stands, the whole party takes 20% less damage.", ancient_roots=0.2),
    _t("Song of the Sea", "own", "While the user stands, the whole party heals 1/12 of its max HP at the end of "
       "each round.", party_regen=8.33),
    _t("Freeze-Dry", "own", "Ice Beam freezes 30% of the time.", ("Ice Beam", {"status_chance": 20})),
    _t("Sheer Cold", "own", "Blizzard hits every enemy at full damage, and freezes 20% of the time.",
       ("Blizzard", {"spread": True, "spread_share": 1.0, "status_chance": 10})),
    _t("Ice Age", "own", "Frozen enemies take 80% more damage from the user.", prey__freeze=0.8),
    _t("Surf", "own", "Water Gun hits much harder: 95 power, and hits every enemy at full damage.",
       ("Water Gun", {"power": 95, "spread": True})),
    # Gastly: haunting, and Gengar's curses.
    _t("Shadow Lick", "own", "Lick hits harder: 50 power, and paralyzes 40% of the time.",
       ("Lick", {"power": 50, "status_chance": 10})),
    _t("Cursed Body", "own", "Whoever hits the user loses 1/12 of its max HP.", thorns=1 / 12),
    _t("Shadow Reach", "own", "Night Shade hits every enemy.", ("Night Shade", {"spread": True})),
    _t("Shadow Ball", "own", "Lick hits much harder: 90 power, and confuses 30% of the time.",
       ("Lick", {"power": 90, "confuse": 30})),
    # Cubone: a lonely little one and its bone.
    _t("Thick Club", "own", "Bone Club and Bonemerang deal 30% more.",
       ("Bone Club", {"scale": 0.3}), ("Bonemerang", {"scale": 0.3})),
    _t("Mother's Memory", "own", "Below 1/3 HP, the user's Ground and Normal moves deal 1.5× damage.",
       pinch__ground=0.5, pinch__normal=0.5),
    _t("Skull Helm", "own", "Super-effective hits on the user deal 40% less damage.", filter=0.4),
    _t("Bone Zone", "own", "Bonemerang hits every enemy.", ("Bonemerang", {"spread": True})),
    _t("Bone Rush", "own", "Bone Club hits every enemy at full damage, and makes them flinch 30% of the time.",
       ("Bone Club", {"spread": True, "flinch": 20})),
    _t("Guardian Spirit", "own", "The first hit the user takes in each battle deals no damage, and a hit that "
       "would knock it out has a 30% chance to leave it 1 HP.", sturdy=1.0, endure=30),
    _t("Bone Shield", "own", "While the user stands, the whole party takes 20% less damage.", ancient_roots=0.2),
    # Chansey: the nurse, and its lucky egg.
    _t("Natural Remedy", "own", "Softboiled also cures the status conditions of the user's whole party.",
       ("Softboiled", {"soothe": True})),
    _t("Healing Egg", "own", "Softboiled heals the user's whole party.", ("Softboiled", {"rally": True})),
    _t("Blissful", "own", "While the user stands, the whole party heals 1/8 of its max HP at the end of each round.",
       party_regen=12.5),
    _t("Lucky Egg", "own", "Egg Bomb never misses.", ("Egg Bomb", {"sure_hit": True})),
    _t("Egg Barrage", "own", "Egg Bomb hits every enemy, the others at 60% damage.",
       ("Egg Bomb", {"spread": True, "spread_share": 0.6})),
    _t("Lucky Punch", "own", "+30% chance of critical hits.", crit=30),
    _t("Golden Egg", "own", "Egg Bomb hits every enemy at full damage, and never misses.",
       ("Egg Bomb", {"spread": True, "spread_share": 1.0, "sure_hit": True})),
    # Scyther: blades and speed.
    _t("X-Scissor", "own", "Slash hits much harder: 100 power, and is twice as likely to be a critical hit.",
       ("Slash", {"power": 100, "crit_ratio": 3})),
    _t("Fury Cutter", "own", "Quick Attack hits 2 times.", ("Quick Attack", {"hits": (2, 2)})),
    _t("Mantis Speed", "own", "The user has a 60% chance each round to act before the others, and +10% chance "
       "of critical hits.", first=60, crit=10),
    _t("Air Slash", "own", "Wing Attack hits harder: 75 power, and hits every enemy, the others at 60% damage.",
       ("Wing Attack", {"power": 75, "spread": True, "spread_share": 0.6})),
    # Kangaskhan: a parent's guard and a flurry of fists.
    _t("Iron Fist", "own", "Comet Punch, Mega Punch and Dizzy Punch deal 20% more.",
       ("Comet Punch", {"scale": 0.2}), ("Mega Punch", {"scale": 0.2}), ("Dizzy Punch", {"scale": 0.2})),
    _t("Mother's Wrath", "own", "Below 1/3 HP, the user's Normal moves deal 2× damage.", pinch__normal=1.0),
    _t("Dizzy Spin", "own", "Dizzy Punch confuses 50% of the time.", ("Dizzy Punch", {"confuse": 30})),
    _t("Comet Barrage", "own", "Comet Punch hits 3-5 times.", ("Comet Punch", {"hits": (3, 5)})),
    _t("Parental Bond", "own", "Mega Punch hits twice.", ("Mega Punch", {"hits": (2, 2)})),
    # Tauros: the stampede.
    _t("Stampede", "own", "Stomp hits every enemy at full damage.", ("Stomp", {"spread": True})),
    _t("Horn Charge", "own", "Take Down hits harder: 120 power.", ("Take Down", {"power": 120})),
    _t("Anger Point", "own", "Below 1/3 HP, the user's Normal moves deal 2× damage, and it acts first 50% of the "
       "time.", pinch__normal=1.0, first=50),
    _t("Raging Bull", "own", "Take Down hits every enemy at full damage.", ("Take Down", {"spread": True})),
    # Rhyhorn: a drilling horn and rock-hard armor.
    _t("Rock Drill", "own", "Horn Attack becomes a Rock move (with STAB) and hits harder: 90 power.",
       ("Horn Attack", {"type": "rock", "power": 90})),
    _t("Tectonic Rage", "own", "Earthquake hits harder: 130 power.", ("Earthquake", {"power": 130})),
    _t("Rock Armor", "own", "The first hit the user takes in each battle deals no damage, and whoever hits the "
       "user loses 1/8 of its max HP.", sturdy=1.0, thorns=0.125),
    # Exeggcute: a grove that thinks.
    _t("Harvest Sun", "own", "Solar Beam needs no charging.", ("Solar Beam", {"charge": ""})),
    _t("Tropical Canopy", "own", "While the user stands, the whole party takes 20% less damage and heals 1/16 of "
       "its max HP at the end of each round.", ancient_roots=0.2, party_regen=6.25),
    # Hitmonlee: kicks.
    _t("Mind Over Body", "own", "Meditate raises the user's Attack 1 stage more (2 in all).",
       ("Meditate", {"stages": (("attack", 1),)})),
    _t("Rolling Sweep", "own", "Rolling Kick hits every enemy, the others at 60% damage.",
       ("Rolling Kick", {"spread": True, "spread_share": 0.6})),
    _t("Reckless", "own", "Jump Kick and Hi Jump Kick never miss.",
       ("Jump Kick", {"sure_hit": True}), ("Hi Jump Kick", {"sure_hit": True})),
    _t("Hi Jump Mastery", "own", "Hi Jump Kick hits much harder: 120 power.", ("Hi Jump Kick", {"power": 120})),
    _t("Kickmaster", "own", "Mega Kick becomes a Fighting move (with STAB) and never misses.",
       ("Mega Kick", {"type": "fighting", "sure_hit": True})),
    _t("Inner Focus", "own", "+20% chance of critical hits.", crit=20),
    _t("One-Inch Kick", "own", "The user's critical hits deal 2.5× damage (not 1.5×).", sniper=1.0),
    _t("Limber", "own", "At the end of each round, the user has a 40% chance to shake off its status.", shed=40),
    _t("Long Reach", "own", "The user's Fighting moves also hit an enemy next to the target, at 50% damage.",
       ("type:fighting", {"reach": 0.5})),
    _t("Triple Kick", "own", "Double Kick hits 3 times.", ("Double Kick", {"hits": (3, 3)})),
    _t("Whirlwind Kick", "own", "Double Kick hits every enemy.", ("Double Kick", {"spread": True})),
    # Hitmonchan: the elemental punches.
    _t("Elemental Fists", "own", "Fire, Ice and Thunder Punch are 20% more likely to burn, freeze and paralyze.",
       *((p, {"status_chance": 20}) for p in _PUNCHES)),
    _t("Elemental Barrage", "own", "Fire, Ice and Thunder Punch hit harder: 90 power.",
       *((p, {"power": 90}) for p in _PUNCHES)),
    _t("Elemental Storm", "own", "Fire, Ice and Thunder Punch hit every enemy, the others at 50% damage.",
       *((p, {"spread": True, "spread_share": 0.5}) for p in _PUNCHES)),
    _t("Plasma Fists", "own", "Fire, Ice and Thunder Punch never miss and are twice as likely to be critical hits.",
       *((p, {"sure_hit": True, "crit_ratio": 1}) for p in _PUNCHES)),
    _t("Sucker Punch", "own", "Mega Punch always goes first.", ("Mega Punch", {"priority": 1})),
    _t("Knockout Blow", "own", "Mega Punch hits much harder: 120 power, and never misses.",
       ("Mega Punch", {"power": 120, "sure_hit": True})),
    _t("Counter Stance", "own", "Whoever hits the user loses 1/8 of its max HP.", thorns=0.125),
    _t("Dodge and Weave", "own", "The first hit the user takes in each battle deals no damage, and it has a 50% "
       "chance each round to act before the others.", sturdy=1.0, first=50),
    # Mr. Mime: walls nobody can see.
    _t("Invisible Wall", "own", "Barrier raises the user's Defense 1 stage more (3 in all).",
       ("Barrier", {"stages": (("defense", 1),)})),
    _t("Filter", "own", "Super-effective hits on the user deal 40% less damage.", filter=0.4),
    _t("Quick Screen", "own", "Light Screen and Reflect always go first.",
       ("Light Screen", {"priority": 1}), ("Reflect", {"priority": 1})),
    _t("Wall Mime", "own", "Light Screen lasts 2 rounds longer.", ("Light Screen", {"shield": 2})),
    _t("Grand Illusion", "own", "While the user stands, the whole party takes 30% less damage.", ancient_roots=0.3),
    _t("Prank", "own", "The user's status moves always go first.", ("status_moves", {"priority": 1})),
    _t("Mime's Encore", "own", "Meditate raises the Attack of the user's whole party.", ("Meditate", {"rally": True})),
    # Jynx: kisses and frost.
    _t("Perfect Kiss", "own", "Lovely Kiss never misses, and works 20% more often.",
       ("Lovely Kiss", {"sure_hit": True, "status_chance": 20})),
    _t("Sweet Kiss", "own", "Lovely Kiss works on every enemy, each at half the chance (one alone: the full "
       "chance).", ("Lovely Kiss", {"spread": True})),
    _t("Kiss of Death", "own", "Sleeping enemies take 60% more damage from the user.", prey__sleep=0.6),
    _t("Eternal Slumber", "own", "Enemies the user puts to sleep sleep 2 rounds longer.",
       ("status:sleep", {"sleep_bonus": 2})),
    _t("Ice Body", "own", "The user heals 1/16 of its max HP at the end of each round.", regen=6.25),
    _t("Frost Queen", "own", "Ice Punch hits every enemy at full damage, and freezes 20% of the time.",
       ("Ice Punch", {"spread": True, "status_chance": 10})),
    # Electabuzz: a living storm.
    _t("Static Field", "own", "Whoever hits the user has a 50% chance to be paralyzed.", retaliate__paralysis=50),
    _t("Plasma Storm", "own", "At the start of each battle, each enemy has a 50% chance to be paralyzed.",
       aura__paralysis=50),
    _t("Thunder Fist", "own", "Thunder Punch hits harder: 100 power, and paralyzes 30% of the time.",
       ("Thunder Punch", {"power": 100, "status_chance": 20})),
    _t("Electric Rush", "own", "Thunder Punch hits every enemy at full damage.", ("Thunder Punch", {"spread": True})),
    # Magmar: flames and smoke.
    _t("Heat Wave", "own", "Flamethrower hits every enemy, the others at 60% damage.",
       ("Flamethrower", {"spread": True, "spread_share": 0.6})),
    _t("Inferno Fist", "own", "Fire Punch hits every enemy at full damage, and burns 30% of the time.",
       ("Fire Punch", {"spread": True, "status_chance": 20})),
    _t("Flame Body", "own", "Whoever hits the user has a 30% chance to be burned.", retaliate__burn=30),
    _t("Magma Armor", "own", "The first hit the user takes in each battle deals no damage, and whoever hits the "
       "user has a 50% chance to be burned.", sturdy=1.0, retaliate__burn=50),
    _t("Eruption", "own", "Burned enemies take 60% more damage from the user.", prey__burn=0.6),
    # Pinsir: crushing horns and throws.
    _t("Hyper Cutter", "own", "Vice Grip is twice as likely to be a critical hit.", ("Vice Grip", {"crit_ratio": 1})),
    _t("Guillotine", "own", "Vice Grip hits much harder: 110 power, and is three times as likely to be a critical "
       "hit.", ("Vice Grip", {"power": 110, "crit_ratio": 2})),
    _t("Storm Throw", "own", "Submission hits every enemy, the others at 50% damage.",
       ("Submission", {"spread": True, "spread_share": 0.5})),
    # Tangela: a tangle of vines.
    _t("Vine Snare", "own", "Bind hits every enemy.", ("Bind", {"spread": True})),
    _t("Power Whip", "own", "Slam hits much harder: 120 power, and never misses.",
       ("Slam", {"power": 120, "sure_hit": True})),
    _t("Giga Drain", "own", "Absorb hits much harder: 75 power.", ("Absorb", {"power": 75})),
    _t("Overgrowth", "own", "The user heals 1/8 of its max HP at the end of each round.", regen=12.5),
]

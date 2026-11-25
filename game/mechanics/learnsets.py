"""Each line's moves by level (`talents.TREES` builds its tree from them)."""

# --- moves by level --------------------------------------------------------
# Per line (its species by stage): (move, level, evolution stage needed),
# the moves known from the start (level 0) first; the first of them is the
# basic attack. Levels are Red/Blue's learn levels; strong moves and TMs
# open later and at later stages.

LEARNSETS = {
    ('bulbasaur', 'ivysaur', 'venusaur'): (
        ('Tackle', 0), ('Growl', 0), ('Leech Seed', 7), ('Vine Whip', 13), ('Poison Powder', 20),
        ('Leaf Shield', 22, 1), ('Take Down', 25, 1), ('Razor Leaf', 27), ('Body Slam', 30, 1),
        ('Growth', 34), ('Sleep Powder', 41, 1), ('Solar Beam', 48, 2), ('Double-Edge', 50, 2),
        ('Hyper Beam', 55, 2),
    ),
    ('charmander', 'charmeleon', 'charizard'): (
        ('Scratch', 0), ('Growl', 0), ('Ember', 9), ('Leer', 15), ('Swords Dance', 25, 1), ('Slash', 30),
        ('Flamethrower', 38, 1), ('Fire Spin', 46), ('Fire Blast', 50, 2), ('Earthquake', 55, 2),
    ),
    ('squirtle', 'wartortle', 'blastoise'): (
        ('Tackle', 0), ('Tail Whip', 0), ('Bubble', 8), ('Water Gun', 15), ('Bite', 22), ('Withdraw', 28),
        ('Ice Beam', 30, 1), ('Skull Bash', 35, 2), ('Hydro Pump', 42, 2), ('Blizzard', 55, 2),
    ),
    ('spearow', 'fearow'): (
        ('Peck', 0), ('Growl', 0), ('Leer', 9), ('Fury Attack', 15), ('Swift', 20), ('Whirlwind', 22),
        ('Drill Peck', 29, 1), ('Agility', 36), ('Hyper Beam', 45, 1),
    ),
    ('nidoran_f', 'nidorina', 'nidoqueen'): (
        ('Tackle', 0), ('Growl', 0), ('Scratch', 8), ('Poison Sting', 14), ('Tail Whip', 21),
        ('Body Slam', 25, 1), ('Bite', 29), ('Fury Swipes', 36), ('Double Kick', 43), ('Earthquake', 48, 2),
    ),
    ('nidoran_m', 'nidorino', 'nidoking'): (
        ('Tackle', 0), ('Leer', 0), ('Horn Attack', 8), ('Poison Sting', 14), ('Focus Energy', 21),
        ('Body Slam', 25, 1), ('Fury Attack', 29), ('Thrash', 38, 2), ('Double Kick', 43), ('Earthquake', 48, 2),
    ),
    ('pidgey', 'pidgeotto', 'pidgeot'): (
        ('Gust', 0), ('Sand-Attack', 5), ('Quick Attack', 12), ('Whirlwind', 19), ('Wing Attack', 28),
        ('Double-Edge', 35, 2), ('Agility', 36), ('Sky Attack', 44, 2),
    ),
    ('rattata', 'raticate'): (
        ('Tackle', 0), ('Tail Whip', 0), ('Quick Attack', 7), ('Focus Energy', 23), ('Hyper Fang', 25, 1),
        ('Body Slam', 25, 1), ('Super Fang', 35, 1), ('Hyper Beam', 45, 1),
    ),
    ('caterpie', 'metapod', 'butterfree'): (
        ('Tackle', 0), ('String Shot', 0), ('Harden', 7, 1), ('Confusion', 12, 2), ('Poison Powder', 15, 2),
        ('Stun Spore', 16, 2), ('Sleep Powder', 17, 2), ('Supersonic', 21, 2), ('Mega Drain', 25, 2),
        ('Whirlwind', 26, 2), ('Psybeam', 32, 2),
    ),
    ('weedle', 'kakuna', 'beedrill'): (
        ('Poison Sting', 0), ('String Shot', 0), ('Harden', 7, 1), ('Fury Attack', 12, 2),
        ('Focus Energy', 16, 2), ('Twineedle', 20, 2), ('Swords Dance', 25, 2), ('Pin Missile', 30, 2),
        ('Agility', 35, 2),
    ),
    ('oddish', 'gloom', 'vileplume'): (
        ('Absorb', 0), ('Poison Powder', 15), ('Stun Spore', 17), ('Sleep Powder', 19), ('Acid', 24),
        ('Mega Drain', 25, 1), ('Petal Dance', 33), ('Solar Beam', 46, 2),
    ),
    ('goldeen', 'seaking'): (
        ('Peck', 0), ('Tail Whip', 0), ('Water Gun', 10), ('Supersonic', 19), ('Horn Attack', 24),
        ('Bubble Beam', 24), ('Fury Attack', 30), ('Ice Beam', 40, 1), ('Double-Edge', 42, 1),
        ('Agility', 54),
    ),
    ('staryu', 'starmie'): (
        ('Tackle', 0), ('Water Gun', 17), ('Harden', 22), ('Bubble Beam', 24), ('Thunder Wave', 26),
        ('Recover', 27), ('Swift', 32), ('Psychic', 36, 1), ('Thunderbolt', 38, 1), ('Ice Beam', 40, 1),
        ('Hydro Pump', 47, 1),
    ),
    ('abra', 'kadabra', 'alakazam'): (
        ('Confusion', 0), ('Kinesis', 0), ('Thunder Wave', 12), ('Body Slam', 25, 1), ('Psybeam', 27, 1),
        ('Recover', 31, 1), ('Psychic', 38, 1), ('Reflect', 42), ('Hyper Beam', 50, 2),
    ),
    ('venonat', 'venomoth'): (
        ('Tackle', 0), ('Supersonic', 24), ('Confusion', 27), ('Poison Powder', 30), ('Leech Life', 35),
        ('Double-Edge', 36, 1), ('Stun Spore', 38), ('Psybeam', 43), ('Sleep Powder', 46),
        ('Psychic', 51, 1),
    ),
    # (Gen 1's Meowth and Mankey; Mankey also gets Machop's Low Kick, so
    # it has a Fighting move before Seismic Toss.)
    ('meowth', 'persian'): (
        ('Scratch', 0), ('Growl', 0), ('Bite', 12), ('Pay Day', 17), ('Screech', 24), ('Fury Swipes', 33),
        ('Slash', 44, 1),
    ),
    # (Gen 1's: the S.S. Anne's sailors' and gentlemen's Pokémon.)
    ('machop', 'machoke', 'machamp'): (
        ('Karate Chop', 0), ('Low Kick', 20), ('Leer', 25), ('Focus Energy', 32), ('Seismic Toss', 39),
        ('Submission', 46, 1),
    ),
    ('tentacool', 'tentacruel'): (
        ('Acid', 0), ('Supersonic', 7), ('Wrap', 13), ('Poison Sting', 18), ('Water Gun', 22), ('Constrict', 27),
        ('Barrier', 33), ('Screech', 40), ('Hydro Pump', 48, 1),
    ),
    ('growlithe', 'arcanine'): (
        ('Bite', 0), ('Roar', 0), ('Ember', 18), ('Leer', 23), ('Take Down', 30), ('Agility', 39),
        ('Flamethrower', 50, 1),
    ),
    # (Gen 1's; Voltorb also gets Thunder Shock early, so it has an Electric move.)
    ('voltorb', 'electrode'): (
        ('Tackle', 0), ('Screech', 0), ('Thunder Shock', 12), ('Sonic Boom', 17), ('Self-Destruct', 22),
        ('Light Screen', 29), ('Swift', 36), ('Explosion', 43, 1),
    ),
    ('magnemite', 'magneton'): (
        ('Tackle', 0), ('Sonic Boom', 21), ('Thunder Shock', 25), ('Supersonic', 29), ('Thunder Wave', 35),
        ('Swift', 41), ('Screech', 47),
    ),
    ('mankey', 'primeape'): (
        ('Scratch', 0), ('Leer', 0), ('Karate Chop', 15), ('Low Kick', 18), ('Fury Swipes', 21),
        ('Focus Energy', 27), ('Seismic Toss', 33), ('Thrash', 39, 1),
    ),
    ('bellsprout', 'weepinbell', 'victreebel'): (
        ('Vine Whip', 0), ('Growth', 0), ('Wrap', 13), ('Poison Powder', 15), ('Sleep Powder', 18),
        ('Stun Spore', 21), ('Acid', 26), ('Swords Dance', 30, 1), ('Razor Leaf', 33), ('Slam', 42, 1),
    ),
    ('pikachu', 'raichu'): (
        ('Thunder Shock', 0), ('Growl', 0), ('Thunder Wave', 9), ('Quick Attack', 16), ('Swift', 26),
        ('Thunderbolt', 30), ('Agility', 33), ('Thunder', 43),
    ),
    ('shellder', 'cloyster'): (
        ('Tackle', 0), ('Withdraw', 0), ('Water Gun', 10), ('Supersonic', 18), ('Clamp', 23),
        ('Bubble Beam', 25), ('Aurora Beam', 30), ('Spike Cannon', 35, 1), ('Leer', 39), ('Ice Beam', 50),
        ('Blizzard', 55, 1),
    ),
    ('psyduck', 'golduck'): (
        ('Scratch', 0), ('Water Gun', 8), ('Bubble Beam', 20), ('Tail Whip', 28), ('Confusion', 36),
        ('Fury Swipes', 43), ('Ice Beam', 45, 1), ('Hydro Pump', 52, 1),
    ),
    ('horsea', 'seadra'): (
        ('Bubble', 0), ('Smokescreen', 19), ('Bubble Beam', 20), ('Leer', 24), ('Water Gun', 30),
        ('Agility', 37), ('Ice Beam', 40, 1), ('Hydro Pump', 45, 1),
    ),
    ('geodude', 'graveler', 'golem'): (
        ('Tackle', 0), ('Defense Curl', 11), ('Rock Throw', 16), ('Rock Slide', 25, 1), ('Harden', 26),
        ('Body Slam', 30, 1), ('Earthquake', 35, 2), ('Dig', 35, 2),
    ),
    ('onix',): (
        ('Tackle', 0), ('Screech', 0), ('Bind', 15), ('Rock Throw', 19), ('Rock Slide', 28), ('Slam', 33),
        ('Earthquake', 38), ('Harden', 43),
    ),
    # The Battle Tower's strong lines (and Mew's Pokémon): Gen 1's moves, as far
    # as the game has them. No talent trees yet: just their moves.
    ('dratini', 'dragonair', 'dragonite'): (
        ('Wrap', 0), ('Leer', 0), ('Thunder Wave', 10), ('Dragon Rage', 18), ('Agility', 24), ('Slam', 30),
        ('Body Slam', 36, 1), ('Wing Attack', 40, 2), ('Hyper Beam', 50, 1),
    ),
    ('aerodactyl',): (
        ('Wing Attack', 0), ('Agility', 0), ('Supersonic', 33), ('Bite', 38), ('Take Down', 45), ('Rock Slide', 48),
        ('Hyper Beam', 54),
    ),
    ('magikarp', 'gyarados'): (
        ('Tackle', 0), ('Splash', 0), ('Bite', 20, 1), ('Dragon Rage', 25, 1), ('Leer', 32, 1), ('Hydro Pump', 41, 1),
        ('Hyper Beam', 52, 1),
    ),
    ('lapras',): (
        ('Water Gun', 0), ('Growl', 0), ('Sing', 16), ('Body Slam', 25), ('Confuse Ray', 31), ('Ice Beam', 38),
        ('Hydro Pump', 46), ('Blizzard', 52),
    ),
    ('gastly', 'haunter', 'gengar'): (
        ('Lick', 0), ('Confuse Ray', 0), ('Night Shade', 0), ('Hypnosis', 27), ('Psychic', 35, 2),
        ('Thunderbolt', 40, 2),
    ),
    # (Gen 1's.)
    ('cubone', 'marowak'): (
        ('Bone Club', 0), ('Growl', 0), ('Leer', 25), ('Focus Energy', 31), ('Thrash', 38),
        ('Bonemerang', 43),
    ),
    # (Gen 1's; Defense Curl for Amnesia.)
    ('snorlax',): (
        ('Headbutt', 0), ('Defense Curl', 0), ('Rest', 0), ('Body Slam', 35), ('Harden', 41), ('Double-Edge', 48),
        ('Hyper Beam', 56),
    ),
    ('chansey',): (
        ('Pound', 0), ('Double Slap', 0), ('Sing', 24), ('Growl', 30), ('Softboiled', 34), ('Defense Curl', 38),
        ('Light Screen', 44), ('Seismic Toss', 46), ('Egg Bomb', 48), ('Double-Edge', 54),
    ),
    ('scyther',): (
        ('Quick Attack', 0), ('Leer', 17), ('Focus Energy', 20), ('Slash', 24), ('Swords Dance', 29), ('Agility', 36),
        ('Wing Attack', 42),
    ),
    ('kangaskhan',): (
        ('Comet Punch', 0), ('Bite', 26), ('Tail Whip', 31), ('Mega Punch', 36), ('Leer', 41), ('Dizzy Punch', 46),
    ),
    ('tauros',): (
        ('Tackle', 0), ('Stomp', 21), ('Tail Whip', 28), ('Body Slam', 35), ('Take Down', 44), ('Hyper Beam', 51),
    ),
    ('rhyhorn', 'rhydon'): (
        ('Horn Attack', 0), ('Stomp', 30), ('Tail Whip', 35), ('Fury Attack', 40), ('Rock Slide', 44),
        ('Take Down', 48, 1), ('Earthquake', 50, 1),
    ),
    ('exeggcute', 'exeggutor'): (
        ('Confusion', 0), ('Hypnosis', 0), ('Reflect', 25), ('Leech Seed', 28), ('Stomp', 28, 1), ('Stun Spore', 32),
        ('Egg Bomb', 35, 1), ('Psychic', 40, 1), ('Solar Beam', 45), ('Sleep Powder', 48),
    ),
    ('jynx',): (
        ('Pound', 0), ('Lovely Kiss', 0), ('Ice Punch', 31), ('Double Slap', 39), ('Psychic', 44), ('Body Slam', 47),
        ('Blizzard', 55),
    ),
    ('electabuzz',): (
        ('Quick Attack', 0), ('Thunder Shock', 0), ('Leer', 34), ('Screech', 37), ('Thunder Punch', 42),
        ('Light Screen', 49), ('Thunder', 54),
    ),
    ('magmar',): (
        ('Ember', 0), ('Leer', 36), ('Confuse Ray', 39), ('Fire Punch', 43), ('Smog', 48), ('Flamethrower', 55),
    ),
    ('tangela',): (
        ('Constrict', 0), ('Bind', 0), ('Absorb', 29), ('Poison Powder', 32), ('Stun Spore', 36),
        ('Sleep Powder', 39), ('Slam', 45), ('Growth', 49),
    ),
    ('pinsir',): (
        ('Vice Grip', 0), ('Seismic Toss', 25), ('Harden', 30), ('Slash', 36), ('Swords Dance', 49),
        ('Submission', 52),
    ),
    ('drowzee', 'hypno'): (
        ('Pound', 0), ('Hypnosis', 0), ('Confusion', 17), ('Headbutt', 24), ('Poison Gas', 29), ('Psychic', 32),
        ('Meditate', 37), ('Psybeam', 40, 1),
    ),
    ('diglett', 'dugtrio'): (
        ('Scratch', 0), ('Growl', 15), ('Sand-Attack', 24), ('Slash', 31), ('Dig', 35, 1),
        ('Rock Slide', 35, 1), ('Earthquake', 40, 1),
    ),
    ('sandshrew', 'sandslash'): (
        ('Scratch', 0), ('Sand-Attack', 10), ('Slash', 17), ('Poison Sting', 24), ('Swift', 31),
        ('Dig', 35, 1), ('Fury Swipes', 38), ('Rock Slide', 40, 1), ('Earthquake', 45, 1),
    ),
    ('ekans', 'arbok'): (
        ('Wrap', 0), ('Leer', 0), ('Poison Sting', 10), ('Bite', 17), ('Glare', 24), ('Screech', 31),
        ('Dig', 35, 1), ('Acid', 38),
    ),
    ('jigglypuff', 'wigglytuff'): (
        ('Pound', 0), ('Sing', 0), ('Defense Curl', 19), ('Double Slap', 24), ('Rest', 29),
        ('Body Slam', 34), ('Double-Edge', 39),
    ),
    # (Gen 1's; Team Rocket's.)
    ('koffing', 'weezing'): (
        ('Tackle', 0), ('Smog', 0), ('Sludge', 32), ('Smokescreen', 37), ('Self-Destruct', 40),
        ('Explosion', 48, 1),
    ),
    ('grimer', 'muk'): (
        ('Pound', 0), ('Poison Gas', 30), ('Sludge', 37), ('Harden', 42), ('Screech', 48),
    ),
    ('zubat', 'golbat'): (
        ('Leech Life', 0), ('Supersonic', 10), ('Bite', 15), ('Confuse Ray', 21), ('Wing Attack', 28),
        ('Swift', 32), ('Double-Edge', 38, 1),
    ),
    ('paras', 'parasect'): (
        ('Scratch', 0), ('Stun Spore', 13), ('Leech Life', 20), ('Mega Drain', 24), ('Spore', 27),
        ('Slash', 34), ('Growth', 41), ('Solar Beam', 44, 1),
    ),
    ('clefairy', 'clefable'): (
        ('Pound', 0), ('Growl', 0), ('Sing', 13), ('Double Slap', 18), ('Body Slam', 30, 1),
        ('Thunder Wave', 34), ('Defense Curl', 39), ('Psychic', 40, 1), ('Rest', 44),
    ),
}

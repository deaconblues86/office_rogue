'''
Contains current Item use functions and placeholder specialized work/mob functions
Expectation is that work functions return the items wear/dirtiness so as to reduce its durability/cleanliness
 - Given that most of this just targets specific Mob attributes and applies some kind
   of modifier I'm sure it could dumped into a JSON format if so desired
'''

from random import randint
from constants import colors


def mob_fired(mob):
    mob.broadcast(mob.name.capitalize() + " is fired!", "orange")
    mob.char = "%"
    mob.color = colors["dark_red"]
    mob.blocks = False
    mob.name = "remains of " + mob.name
    mob.state = "fired"
    mob.fired = True


def mob_quits(mob):
    mob.broadcast(mob.name.capitalize() + " quits!", "orange")
    mob.char = "%"
    mob.color = colors["dark_red"]
    mob.blocks = False
    mob.name = "remains of " + mob.name
    mob.state = "fired"
    mob.fired = True


def cellphone_func(user):
    user.mood = min(user.mood + 25, user.max_mood)
    user.broadcast(user.name.capitalize() + " plays on their cellphone", "white")
    user.state = "success: " + user.state
    user.occupied += 6
    return randint(5, 10), 0  # Wearing out / Making object dirty


def toilet_func(user):
    user.bladder = user.max_bladder
    user.bowels = user.max_bowels
    user.broadcast(user.name.capitalize() + " uses the toilet", "white")
    user.state = "success: " + user.state
    user.occupied += 4
    return randint(5, 10), randint(10, 15)  # Wearing out / Making object dirty


def urinal_func(user):
    user.bladder = user.max_bladder
    user.broadcast(user.name.capitalize() + " uses the urinal", "white")
    user.state = "success: " + user.state
    user.occupied += 2
    return randint(5, 10), randint(5, 10)  # Wearing out / Making object dirty


def coffee_func(user):
    user.energy = user.max_energy
    user.thirst = min(user.thirst + 25, user.max_thirst)
    user.bladder = max(user.bladder - 10, 0)
    user.bowels = max(user.bowels - 10, 0)
    user.broadcast(user.name.capitalize() + " gets some coffee", "white")
    user.state = "success: " + user.state
    user.occupied += 2
    return randint(5, 10), 0  # Wearing out / Making object dirty


def water_func(user):
    user.thirst = min(user.thirst + 50, user.max_thirst)
    user.bladder = max(user.bladder - 10, 0)
    user.broadcast(user.name.capitalize() + " drinks some water", "white")
    user.state = "success: " + user.state
    return 50, 0  # Wearing out / Making object dirty


def snack_func(user):
    user.hunger = min(user.hunger + 50, user.max_hunger)
    user.bowels = max(user.bowels - 10, 0)
    user.broadcast(user.name.capitalize() + " eats a snack", "white")
    user.state = "success: " + user.state
    return 25, 0  # Wearing out / Making object dirty


def terminal_func(user):
    energy_ratio = float(user.energy) / float(user.max_energy)
    work_gain = int(user.max_work * (energy_ratio * 0.3))
    user.work = min(user.work + work_gain, user.max_work)
    user.energy = max(int(user.energy - (work_gain * 0.25)), 0)
    user.broadcast(user.name.capitalize() + " uses their terminal", "white")
    user.state = "success: " + user.state
    user.occupied += 8
    return randint(5, 10), 0  # Wearing out / Making object dirty


def desk_func(user):
    energy_ratio = user.energy / user.max_energy
    work_gain = int(user.max_work * (energy_ratio * 0.15))
    user.work = min(user.work + work_gain, user.max_work)
    user.energy = max(int(user.energy - (work_gain * 0.5)), 0)
    user.broadcast(user.name.capitalize() + " uses their desk", "white")
    user.occupied += 8
    return randint(5, 10), 0  # Wearing out / Making object dirty


def repair_func(user, target):
    energy_ratio = user.energy / user.max_energy
    work_gain = int(user.max_work * (energy_ratio * 0.3))
    user.work = min(user.work + work_gain, user.max_work)
    user.energy = max(int(user.energy - (work_gain * 0.25)), 0)
    user.broadcast(user.name.capitalize() + " repairs the " + target.name.capitalize(), "white")
    user.state = "success: " + user.state

    # Currently setting up repair to add durability to target equal to work put it
    target.durability = min(target.durability + work_gain, 100)
    target.state = ""
    target.color = target.orig_color


def clean_func(target):
    # Function to handle clean up of waste & restore work for cleaners
    # TODO: Use Funcs tend to operate on the user, this one needs to operate on itself
    # Dump in favor of something like a work_func
    # Could be repurpsed to impact mood, but won't be used at present since doesn't block
    return 100

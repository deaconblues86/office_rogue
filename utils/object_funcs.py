'''
Contains current Item use functions and placeholder specialized work/mob functions
Expectation is that work functions return the items wear so as to reduce its durability
 - Given that most of this just targets specific Mob attributes and applies some kind
   of modifier I'm sure it could dumped into a JSON format if so desired
'''

from random import randint
from contants import colors


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


def toilet_func(target):
    target.bladder = target.max_bladder
    target.bowels = target.max_bowels
    target.broadcast(target.name.capitalize() + " uses the toilet", "white")
    target.state = "success: " + target.state
    return randint(5, 10)  # Wearing out object


def urinal_func(target):
    target.bladder = target.max_bladder
    target.broadcast(target.name.capitalize() + " uses the urinal", "white")
    target.state = "success: " + target.state
    return randint(5, 10)  # Wearing out object


def terminal_func(target):
    energy_ratio = float(target.energy) / float(target.max_energy)
    work_gain = int(target.max_work * (energy_ratio * 0.3))
    target.work = min(target.work + work_gain, target.max_work)
    target.energy = max(int(target.energy - (work_gain * 0.25)), 0)
    target.broadcast(target.name.capitalize() + " uses their terminal", "white")
    target.state = "success: " + target.state
    return randint(5, 10)  # Wearing out object


def desk_func(target):
    energy_ratio = target.energy / target.max_energy
    work_gain = int(target.max_work * (energy_ratio * 0.15))
    target.work = min(target.work + work_gain, target.max_work)
    target.energy = max(int(target.energy - (work_gain * 0.5)), 0)
    target.broadcast(target.name.capitalize() + " uses their desk", "white")
    return randint(5, 10)  # Wearing out object


def repair_func(worker, target):
    energy_ratio = target.energy / target.max_energy
    work_gain = int(target.max_work * (energy_ratio * 0.3))
    worker.work = min(worker.work + work_gain, worker.max_work)
    worker.energy = max(int(worker.energy - (work_gain * 0.25)), 0)
    target.broadcast(worker.name.capitalize() + " repairs the " + target.name.capitalize(), "white")
    worker.state = "success: " + worker.state

    # Currently setting up repair to add durability to target equal to work put it
    target.durability += work_gain
    target.state = ""
    target.color = target.orig_color


def coffee_func(target):
    target.energy = target.max_energy
    target.thirst = min(
        int(target.thirst + (target.max_thirst * 0.25)),
        target.max_thirst,
    )
    target.bladder = max(
        int(target.bladder - (target.max_bladder * 0.1)), 0
    )
    target.bowels = max(
        int(target.bowels - (target.max_bowels * 0.1)), 0
    )
    target.broadcast(target.name.capitalize() + " gets some coffee", "white")
    target.state = "success: " + target.state
    return randint(5, 10)  # Wearing out object


def water_func(target):
    target.thirst = min(
        target.thirst + (target.max_thirst * 0.75),
        target.max_thirst,
    )
    target.bladder = max(
        target.bladder - (target.max_bladder * 0.1), 0
    )
    target.broadcast(target.name.capitalize() + " drinks some water", "white")
    target.state = "success: " + target.state
    return 50


def snack_func(target):
    target.hunger = min(
        target.hunger + (target.max_hunger * 0.5),
        target.max_hunger,
    )
    target.bowels = max(
        target.bowels - (target.max_bowels * 0.1), 0
    )
    target.broadcast(target.name.capitalize() + " eats a snack", "white")
    target.state = "success: " + target.state
    return 25


def clean_func(target):
    # Function to handle clean up of waste & restore work for cleaners
    # TODO: Use Funcs tend to operate on the user, this one needs to operate on itself
    # Dump in favor of something like a work_func
    # Could be repurpsed to impact mood, but won't be used at present since doesn't block
    return 100

def sluggish(worker):
    worker.energy_drain = worker.energy_drain * 1.25
    
def workaholic(worker):
    worker.work_gain = worker.work_gain * 1.25
    if worker.work_gain == 0:
        worker.happiness_drain = worker.happiness_drain * 1.25

def chatty(worker):
    worker.social_drain = worker.social_drain * 1.25
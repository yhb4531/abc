import random

def get_human_delay(base_time):
    return max(0.1, random.gauss(base_time, base_time * 0.2))

def get_jitter(amount=15):
    return random.randint(-amount, amount)
"""Fake torch: deterministic subprocess tests only, never a real model."""
def set_num_threads(number):
    assert number == 2

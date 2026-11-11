#!/usr/bin/env python3
"""Your first Python script. Change the name and run it again!"""
from datetime import datetime

name = "Claudius"
hour = datetime.now().hour
greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"
print(f"{greeting}, {name}! 👋")
print(f"2 to the power of 100 is {2 ** 100}")
for i in range(1, 6):
    print("★" * i)

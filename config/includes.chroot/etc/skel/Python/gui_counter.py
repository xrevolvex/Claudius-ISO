#!/usr/bin/env python3
"""A tiny window app made with tkinter, which comes with Python."""
import tkinter as tk

root = tk.Tk()
root.title("Claudius counter")
root.configure(bg="#0d1122", padx=30, pady=24)
count = tk.IntVar(value=0)

tk.Label(root, textvariable=count, font=("Cantarell", 48, "bold"), fg="#ffb547", bg="#0d1122").pack()
row = tk.Frame(root, bg="#0d1122")
row.pack(pady=12)
for text, step in (("−", -1), ("+", 1)):
    tk.Button(row, text=text, width=4, font=("Cantarell", 16), command=lambda s=step: count.set(count.get() + s),
              bg="#22305c", fg="white", activebackground="#ff7a45", relief="flat").pack(side="left", padx=6)
tk.Button(root, text="Reset", command=lambda: count.set(0), bg="#161c36", fg="#c8cde0", relief="flat").pack()
root.mainloop()

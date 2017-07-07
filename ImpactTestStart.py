import os
from Tkinter import *
import ttk

from abaqus import mdb, session


class ImpactTestGUI():
    def __init__(self):
        # Initialize
        self.master = Tk()
        self.PROCEED = Button(self.master)
        self.notebook = ttk.Notebook(self.master)
        self.frame = Frame(self.notebook)
        # Labels
        self.projectileLabel = ttk.Label(self.frame, text="Projectile type")
        self.armorRadiusLabel = ttk.Label(self.frame, text="Armor plate radius")
        self.armorLayersLabel = ttk.Label(self.frame, text="Armor layers - top towards projectile")
        self.armorObliquityLabel = ttk.Label(self.frame, text="Armor obliquity - 0 indicates normal to projectile")
        # Configure
        self.configureWidgets()
        # Start
        self.master.mainloop()

    def configureWidgets(self):
        # AUXILIARY
        self.master.title("Armor impact menu")
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)
        self.notebook.grid(row=0, column=0)
        self.frame.grid(row=0, column=0)
        # PROCEED button
        self.PROCEED['text'] = "Proceed"
        self.PROCEED['bg'] = "white"
        self.PROCEED['command'] = self.proceed
        self.PROCEED.pack({'side': 'bottom'})
        # Labels
        self.projectileLabel.grid(column=0, row=0)
        self.armorRadiusLabel.grid(column=0, row=1)
        self.armorLayersLabel.grid(column=0, row=2)
        self.armorObliquityLabel.grid(column=0, row=3)
        # Adjust size
        self.master.minsize(400, 700)


    # TODO: Implement proceed
    def proceed(self):
        # PROCEED code
        self.master.destroy()


def __importParts():
    parts = []
    for part in mdb.models['Model-1'].parts.items():
        if part.name.endswith("Projectile"):
            parts.append(part)
    return parts


def __importMaterials():
    directory = os.listdir(os.path.dirname(os.path.realpath(__file__)) + "/Material")
    materials = []
    for file in directory:
        if file.endswith(".lib"):
            materials.append("material library")
    return materials


def __startWindow():
    gui = ImpactTestGUI()


def run():
    parts = __importParts()
    # materials= __importMaterials()
    __startWindow()

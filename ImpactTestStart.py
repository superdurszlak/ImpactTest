import os
from Tkinter import *
import ttk

from abaqus import mdb, session


class ImpactTestGUI():
    def __init__(self):
        # Initialize
        self.master = Tk()
        self.PROCEED = Button(self.master)
        self.frame = Frame(self.master)
        # Labels
        self.projecileMainLabel = ttk.Label(self.frame, text="Projectile")
        self.projectileLabel = ttk.Label(self.frame, text="Projectile type")
        self.velocityLabel = ttk.Label(self.frame, text="Projectile velocity [m/s]")
        self.armorMainLabel = ttk.Label(self.frame, text="Armor")
        self.armorRadiusLabel = ttk.Label(self.frame, text="Armor plate radius [mm]")
        self.armorLayersLabel = ttk.Label(self.frame, text="No. of armor layers")
        self.armorObliquityLabel = ttk.Label(self.frame, text="Armor obliquity [deg]")
        self.modelMainLabel = ttk.Label(self.frame, text="Mesh")
        self.meshElementSize = ttk.Label(self.frame, text="Element size [mm]")
        # Variables
        self.projectile = StringVar()
        self.projectileParts = [x for x in self.parts()]
        self.velocity = StringVar()
        self.obliquity = StringVar()
        self.radius = StringVar()
        self.layersCount = StringVar()
        self.elementSize = StringVar()
        # Editable fields
        self.projectileField = ttk.Combobox(
            self.frame,
            textvariable=self.projectile,
            values=self.projectileParts
        )
        self.velocityField = ttk.Entry(
            self.frame,
            textvariable=self.velocity
        )
        self.obliquityField = ttk.Entry(
            self.frame,
            textvariable=self.obliquity
        )
        self.radiusField = ttk.Entry(
            self.frame,
            textvariable=self.radius
        )
        self.meshElementSizeField = ttk.Entry(
            self.frame,
            textvariable=self.elementSize
        )
        self.layersCountField = Spinbox(
            self.frame,
            values=range(1, 10),
            textvariable=self.layersCount
        )
        # Configure
        self.configureWidgets()
        # Start
        self.master.mainloop()

    def configureWidgets(self):
        # AUXILIARY
        self.master.title("Armor impact menu")
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)
        self.frame.grid(row=0, column=0)
        # ENTRIES
        self.projectileField.grid(column=1, row=1, sticky=W)
        self.velocityField.grid(column=1, row=2, sticky=W)
        self.radiusField.grid(column=1, row=4, sticky=W)
        self.obliquityField.grid(column=1, row=5, sticky=W)
        self.layersCountField.bind("<<ValueChange>>", self.updateLayerList)
        self.layersCountField.grid(column=1, row=6, sticky=W)
        self.meshElementSizeField.grid(column=1, row=8, sticky=W)
        # PROCEED button
        self.PROCEED['text'] = "Proceed"
        self.PROCEED['bg'] = "white"
        self.PROCEED['command'] = self.proceed
        self.PROCEED.grid(column=0, row=1)
        # Labels
        self.projecileMainLabel.grid(column=0, row=0, sticky=W)
        self.projectileLabel.grid(column=0, row=1, sticky=W)
        self.velocityLabel.grid(column=0, row=2, sticky=W)
        self.armorMainLabel.grid(column=0, row=3, sticky=W)
        self.armorRadiusLabel.grid(column=0, row=4, sticky=W)
        self.armorObliquityLabel.grid(column=0, row=5, sticky=W)
        self.armorLayersLabel.grid(column=0, row=6, sticky=W)
        self.modelMainLabel.grid(column=0, row=7, sticky=W)
        self.meshElementSize.grid(column=0, row=8, sticky=W)
        # Adjust size
        self.master.minsize(400, 700)


    # TODO: Implement proceed
    def proceed(self):
        # PROCEED code
        self.master.destroy()

    # TODO: Implement layer config change
    def updateLayerList(self, arg):
        pass

    def parts(self):
        for p in mdb.models['Model-1'].parts.keys():
            if p.startswith('Projectile'):
                yield p


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
    # parts = __importParts()
    # materials= __importMaterials()
    __startWindow()

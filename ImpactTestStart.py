import json
import os

import math
from pickle import Unpickler

from Tkinter import *
import ttk
import tkFileDialog

from abaqus import mdb, session
from abaqusConstants import *
from material import createMaterialFromDataString

from ImpactTestKernel import ImpactTestKernel

availableParts = []
class ImpactTestGUI():
    def __init__(self):
        # Initialize
        self.master = Tk()
        self.PROCEED = Button(self.master)
        self.SAVE = Button(self.master)
        self.LOAD = Button(self.master)
        self.frame = Frame(self.master, height=300)
        self.layup = Frame(self.master, height=300)
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
        self.layerNoLabel = ttk.Label(self.layup, text="Layer")
        self.materialLabel = ttk.Label(self.layup, text="Material")
        self.layerThicknessLabel = ttk.Label(self.layup, text="Thickness [mm]")
        # Variables
        self.projectile = StringVar()
        self.projectileParts = [x for x in self.parts()]
        self.armorMaterials = [x for x in self.materials()]
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
            textvariable=self.velocity, validate="focusout", validatecommand=self.verifyFloats
        )
        self.obliquityField = ttk.Entry(
            self.frame,
            textvariable=self.obliquity, validate="focusout", validatecommand=self.verifyFloats
        )
        self.radiusField = ttk.Entry(
            self.frame,
            textvariable=self.radius, validate="focusout", validatecommand=self.verifyFloats
        )
        self.meshElementSizeField = ttk.Entry(
            self.frame,
            textvariable=self.elementSize, validate="focusout", validatecommand=self.verifyFloats
        )
        self.layersCountField = Spinbox(
            self.frame,
            values=range(1, 10),
            textvariable=self.layersCount,
            command=self.updateLayerList
        )
        self.layupWidgets = []
        # Configure
        self.configureWidgets()
        self.createLayupRow(0)
        # Start
        self.master.mainloop()

    def configureWidgets(self):
        # AUXILIARY
        self.configureAuxiliary()
        # ENTRIES
        self.configureEntries()
        # Labels
        self.configureLabels()
        # PROCEED button
        self.PROCEED['text'] = "Proceed"
        self.PROCEED['bg'] = "white"
        self.PROCEED['command'] = self.proceed
        self.PROCEED.grid(column=2, row=2, sticky='SW')
        # SAVE button
        self.SAVE['text'] = "Save..."
        self.SAVE['bg'] = "white"
        self.SAVE['command'] = self.save
        self.SAVE.grid(column=1, row=2, sticky='S')
        # LOAD button
        self.LOAD['text'] = "Load..."
        self.LOAD['bg'] = "white"
        self.LOAD['command'] = self.load
        self.LOAD.grid(column=0, row=2, sticky='SE')


    # TODO: Implement proceed
    def proceed(self):
        config = self.prepareModelConfig()
        self.master.destroy()
        ImpactTestKernel(config).run()
    def save(self):
        config = self.prepareModelConfig()
        file = tkFileDialog.asksaveasfile(
            mode='wb',
            defaultextension='.cfg',
            filetypes=[
                ('Configuration files', '.cfg')
            ]
        )
        if file is not None:
            file.write(json.dumps(config))
            file.close()

    def load(self):
        opts = {
            'filetypes': [('Configuration file', '.cfg')]
        }
        filename=tkFileDialog.askopenfilename(**opts)
        if filename != "":
            file = open(filename, mode='r')
            config = json.load(file)
            self.loadModelFromConfig(config)


    def updateLayerList(self):
        try:
            int(self.layersCount.get())
        except ValueError:
            self.layersCount.set("1")
        finally:
            self.adjustLayup(int(self.layersCount.get()))
        pass

    def parts(self):
        for p in availableParts:
            yield p

    def adjustLayup(self, count):
        while len(self.layupWidgets) > count:
            row = self.layupWidgets[-1]
            for el in row:
                if hasattr(el, "destroy") and callable(el.destroy):
                    el.destroy()
            self.layupWidgets.pop()
        while len(self.layupWidgets) < count:
            self.createLayupRow(len(self.layupWidgets))

    def createLayupRow(self, idx):
        label = ttk.Label(self.layup, text=str(idx+1))
        label.grid(column=0, row=idx+1, sticky='NW')
        matvar = StringVar()
        material = ttk.Combobox(self.layup, textvariable=matvar, values=self.armorMaterials)
        material.grid(column=1, row=idx+1, sticky='NW')
        thickvar = StringVar()
        thickness = ttk.Entry(self.layup, textvariable=thickvar, validate="focusout", validatecommand=self.verifyFloats)
        thickness.grid(column=2, row=idx+1, sticky='NW')
        tup = (label, matvar, material, thickvar, thickness)
        self.layupWidgets.append(tup)

    def materials(self):
        for m in mdb.models['Model-1'].materials.keys():
            yield m

    def verifyFloats(self):
        for (label, matvar, material, thickvar, thickness) in self.layupWidgets:
            self.verifyStringVarFloat(thickvar, treshold=0.5, maximum=150.0)
        self.verifyStringVarFloat(self.radius, treshold=30.0, maximum=55.0)
        self.verifyStringVarFloat(self.obliquity, treshold=0.0, maximum=60.0)
        self.verifyStringVarFloat(self.velocity, treshold=100.0, maximum=2000.0)
        self.verifyStringVarFloat(self.elementSize, treshold=0.05, maximum=2.0)

    def verifyStringVarFloat(self, strvar, treshold=0.0, maximum=None):
        if maximum is None:
            maximum = math.inf
        try:
            t = float(strvar.get())
            if t < treshold:
                strvar.set(treshold)
            if t > maximum:
                strvar.set(maximum)
        except ValueError:
            strvar.set(treshold)

    def configureAuxiliary(self):
        self.master.title("Armor impact menu")
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)
        self.frame.grid(row=0, column=1, sticky='NW')
        self.layup.grid(row=1, column=1, sticky='NW')
        # Minimum window size
        self.master.minsize(400, 700)

    def configureEntries(self):
        self.projectileField.grid(column=1, row=1, sticky='NW')
        self.velocityField.grid(column=1, row=2, sticky='NW')
        self.radiusField.grid(column=1, row=4, sticky='NW')
        self.obliquityField.grid(column=1, row=5, sticky='NW')
        self.layersCountField.grid(column=1, row=6, sticky='NW')
        self.meshElementSizeField.grid(column=1, row=8, sticky='NW')

    def configureLabels(self):
        self.projecileMainLabel.grid(column=0, row=0, sticky='NW')
        self.projectileLabel.grid(column=0, row=1, sticky='NW')
        self.velocityLabel.grid(column=0, row=2, sticky='NW')
        self.armorMainLabel.grid(column=0, row=3, sticky='NW')
        self.armorRadiusLabel.grid(column=0, row=4, sticky='NW')
        self.armorObliquityLabel.grid(column=0, row=5, sticky='NW')
        self.armorLayersLabel.grid(column=0, row=6, sticky='NW')
        self.modelMainLabel.grid(column=0, row=7, sticky='NW')
        self.meshElementSize.grid(column=0, row=8, sticky='NW')
        self.layerNoLabel.grid(column=0, row=0, sticky='NW')
        self.materialLabel.grid(column=1, row=0, sticky='NW')
        self.layerThicknessLabel.grid(column=2, row=0, sticky='NW')

    def prepareModelConfig(self):
        config = {}
        layers = []
        for (label, matvar, material, thickvar, thickness) in self.layupWidgets:
            layers.append({
                'material': matvar.get(),
                'thickness': float(thickvar.get())/1000.0
            })
        config['projectile'] = {
            'type': self.projectile.get(),
            'velocity': float(self.velocity.get()),
        }
        config['armor'] = {
            'radius': float(self.radius.get())/1000.0,
            'obliquity': float(self.obliquity.get()),
            'layers': layers
        }
        config['meshElementSize'] = float(self.elementSize.get())/1000.0
        return config

    def loadModelFromConfig(self, config):
        if 'projectile' in config:
            if 'type' in config['projectile']:
                if config['projectile']['type'] in self.parts():
                    self.projectile.set(config['projectile'][u'type'])
            if 'velocity' in config['projectile']:
                self.velocity.set(round(float(config['projectile']['velocity']), 1))
        if 'armor' in config:
            if 'radius' in config['armor']:
                self.radius.set(round(float(config[u'armor'][u'radius'])*1000.0, 1))
            if 'innerRadius' in config['armor']:
                pass
            if 'obliquity' in config['armor']:
                self.obliquity.set(round(float(config['armor']['obliquity']), 1))
            if 'layers' in config['armor']:
                self.loadLayersFromConfig(config['armor']['layers'])
        if 'meshElementSize' in config:
            self.elementSize.set(round(float(config['meshElementSize'])*1000.0, 3))
        self.verifyFloats()

    def loadLayersFromConfig(self, layers):
        self.adjustLayup(0)
        self.layersCount.set(len(layers))
        self.adjustLayup(len(layers))
        i = 0
        for layer in layers:
            material = ""
            thickness = 0.25
            if 'material' in layer and layer['material'] in self.materials():
                material = layer['material']
            if 'thickness' in layer:
                thickness = round(float(layer['thickness'])*1000.0, 2)
            row = self.layupWidgets[i]
            i += 1
            row[1].set(material)
            row[3].set(thickness)


def __importParts():
    del availableParts[:]
    __directory = os.path.dirname(os.path.realpath(__file__)) + "\\Parts\\"
    if not os.path.exists(__directory):
        os.makedirs(__directory)
    directories = os.listdir(__directory)
    print(__directory)
    for __dir in directories:
        name = __dir
        __dir = __directory + __dir
        if os.path.isdir(__dir):
            print(__dir)
            projectile = __dir+"\\Projectile.sat"
            print(projectile)
            projectile = mdb.openAcis(projectile)
            print("Projectile_"+name)
            casing = mdb.models['Model-1'].PartFromGeometryFile(
                "Casing_"+name,
                projectile,
                THREE_D,
                DEFORMABLE_BODY,
                bodyNum=2
            )
            core = mdb.models['Model-1'].PartFromGeometryFile(
                "Core_"+name,
                projectile,
                THREE_D,
                DEFORMABLE_BODY,
                bodyNum=1
            )
            availableParts.append(name)


def __importMaterials():
    __directory=os.path.dirname(os.path.realpath(__file__)) + "\\Materials\\"
    if not os.path.exists(__directory):
        os.makedirs(__directory)
    directory = os.listdir(__directory)
    materials = []
    for file in directory:
        if file.endswith(".lib"):
            f = open(__directory+"\\"+file, 'r')
            lib = Unpickler(f).load()
            f.close()
            for (a, b, name, c, mat) in lib:
                if b != -1:
                    createMaterialFromDataString('Model-1', mat['Vendor material name'], mat['version'], mat['Data'])
    return materials


def __startWindow():
    session.graphicsOptions.setValues(
        highlightMethodHint=XOR,
        antiAlias=OFF,
        translucencyMode=1
    )
    #session.journalOptions.setValues(replayGeometry=INDEX)
    gui = ImpactTestGUI()


def run():
    __importMaterials()
    __importParts()
    __startWindow()

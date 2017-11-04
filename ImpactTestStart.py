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

# List of available parts to be used in the model
availableParts = []


# Class for plugin's GUI
class ImpactTestGUI():
    # Initialize labels and editable fields
    def __init__(self):
        # Main components and controls
        self.master = Tk()
        self.PROCEED = Button(self.master)
        self.SAVE = Button(self.master)
        self.LOAD = Button(self.master)
        self.frame = Frame(
            self.master,
            height=300
        )
        self.layup = Frame(
            self.master,
            height=300
        )
        # Labels
        self.projecileMainLabel = ttk.Label(
            self.frame,
            text="Projectile"
        )
        self.projectileLabel = ttk.Label(
            self.frame,
            text="Projectile type"
        )
        self.velocityLabel = ttk.Label(
            self.frame,
            text="Projectile velocity [m/s]"
        )
        self.armorMainLabel = ttk.Label(
            self.frame,
            text="Armor"
        )
        self.armorRadiusLabel = ttk.Label(
            self.frame,
            text="Armor plate radius [mm]"
        )
        self.armorLayersLabel = ttk.Label(
            self.frame,
            text="No. of armor layers"
        )
        self.armorObliquityLabel = ttk.Label(
            self.frame,
            text="Armor obliquity [deg]"
        )
        self.modelMainLabel = ttk.Label(
            self.frame,
            text="Mesh"
        )
        self.meshElementSize = ttk.Label(
            self.frame,
            text="Element size [mm]"
        )
        self.modelLabel = ttk.Label(
            self.frame,
            text="Model"
        )
        self.modelNameLabel = ttk.Label(
            self.frame,
            text="Model name"
        )
        self.layerNoLabel = ttk.Label(
            self.layup,
            text="Layer"
        )
        self.materialLabel = ttk.Label(
            self.layup,
            text="Material"
        )
        self.layerThicknessLabel = ttk.Label(
            self.layup,
            text="Thickness [mm]"
        )
        self.layerSpacingLabel = ttk.Label(
            self.layup,
            text="Space behind layer [mm]"
        )
        # Variables
        self.projectile = StringVar()
        self.projectileParts = [x for x in self.parts()]
        self.armorMaterials = [x for x in self.materials()]
        self.velocity = StringVar()
        self.obliquity = StringVar()
        self.radius = StringVar()
        self.layersCount = StringVar()
        self.elementSize = StringVar()
        self.modelName = StringVar()
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
        self.radiusField = ttk.Entry(
            self.frame,
            textvariable=self.radius, validate="focusout", validatecommand=self.verifyFloats
        )
        self.obliquityField = ttk.Entry(
            self.frame,
            textvariable=self.obliquity, validate="focusout", validatecommand=self.verifyFloats
        )
        self.layersCountField = Spinbox(
            self.frame,
            values=range(1, 10),
            textvariable=self.layersCount,
            command=self.updateLayerList
        )
        self.meshElementSizeField = ttk.Entry(
            self.frame,
            textvariable=self.elementSize, validate="focusout", validatecommand=self.verifyFloats
        )
        self.modelNameField = ttk.Entry(
            self.frame,
            textvariable=self.modelName
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
        self.PROCEED.grid(
            column=2,
            row=2,
            sticky='SW'
        )
        # SAVE button
        self.SAVE['text'] = "Save..."
        self.SAVE['bg'] = "white"
        self.SAVE['command'] = self.save
        self.SAVE.grid(
            column=1,
            row=2,
            sticky='S'
        )
        # LOAD button
        self.LOAD['text'] = "Load..."
        self.LOAD['bg'] = "white"
        self.LOAD['command'] = self.load
        self.LOAD.grid(
            column=0,
            row=2,
            sticky='SE'
        )

    # Proceed to model generation by plugin's kernel
    def proceed(self):
        config = self.prepareModelConfig()
        # Set proper model name if nonexistent
        modelName = self.modelName.get()
        if not modelName:
            modelName = "Model-1"
        # GUI isn't needed anymore
        self.master.destroy()
        # Run kernel
        ImpactTestKernel(config, modelName).run()

    # Save model's configuration to JSON-formatted file for later use
    def save(self):
        config = self.prepareModelConfig()
        # Open file save dialog. 'cfg' extension stands for 'configuration' and is customary
        file = tkFileDialog.asksaveasfile(
            mode='wb',
            defaultextension='.cfg',
            filetypes=[
                (
                    'Configuration files',
                    '.cfg'
                )
            ]
        )
        # Write configuration to file if selected
        if file is not None:
            file.write(json.dumps(config))
            file.close()

    # Load previously model configuration
    def load(self):
        opts = {
            'filetypes': [
                (
                    'Configuration file',
                    '.cfg'
                )
            ]
        }
        # Open file open dialog
        filename = tkFileDialog.askopenfilename(**opts)
        # Load configuration from file if any selected
        if filename != "":
            file = open(
                filename,
                mode='r'
            )
            config = json.load(file)
            self.loadModelFromConfig(config)

    # Update layer controls quantity on layersCount spinner value change
    def updateLayerList(self):
        # Fix invalid value if necessary
        try:
            int(self.layersCount.get())
        except ValueError:
            self.layersCount.set("1")
        finally:
            self.adjustLayup(int(self.layersCount.get()))
        pass

    # Yield parts from available parts' names list
    def parts(self):
        for p in availableParts:
            yield p

    # Adjust layer controls to given layers number
    def adjustLayup(self, count):
        # Get rid of extra controls
        while len(self.layupWidgets) > count:
            row = self.layupWidgets[-1]
            for el in row:
                if hasattr(el, "destroy") and callable(el.destroy):
                    el.destroy()
            self.layupWidgets.pop()
        # Create missing controls
        while len(self.layupWidgets) < count:
            self.createLayupRow(len(self.layupWidgets))

    # Create controls for single layer
    def createLayupRow(self, idx):
        # Label
        label = ttk.Label(
            self.layup,
            text=str(idx + 1)
        )
        label.grid(
            column=0,
            row=idx + 1,
            sticky='NW'
        )
        # Material
        matvar = StringVar()
        material = ttk.Combobox(
            self.layup,
            textvariable=matvar,
            values=self.armorMaterials
        )
        material.grid(
            column=1,
            row=idx + 1,
            sticky='NW'
        )
        # Thickness in [mm]
        thickvar = StringVar()
        thickness = ttk.Entry(
            self.layup,
            textvariable=thickvar,
            validate="focusout",
            validatecommand=self.verifyFloats
        )
        thickness.grid(
            column=2,
            row=idx + 1,
            sticky='NW'
        )
        spacevar = StringVar()
        spacing = ttk.Entry(
            self.layup,
            textvariable=spacevar,
            validate="focusout",
            validatecommand=self.verifyFloats
        )
        spacing.grid(
            column=3,
            row=idx + 1,
            sticky='NW'
        )
        tup = (
            label,
            matvar,
            material,
            thickvar,
            thickness,
            spacevar,
            spacing
        )
        self.layupWidgets.append(tup)

    # Yield loaded materials' names
    def materials(self):
        for m in mdb.models['Model-1'].materials.keys():
            yield m

    # Check floats in editable fields for validity
    def verifyFloats(self):
        # Allow layers to be between 0.5 and 150.0 [mm] thick
        for (label, matvar, material, thickvar, thickness, spacevar, spacing) in self.layupWidgets:
            self.verifyStringVarFloat(
                thickvar,
                treshold=0.5,
                maximum=150.0
            )
            self.verifyStringVarFloat(
                spacevar,
                treshold=0.0,
                maximum=100.0
            )
        # Allow target radius to be between 30.0 and 55.0 [mm]. Could be replaced with caliber-dependent radius
        self.verifyStringVarFloat(
            self.radius,
            treshold=30.0,
            maximum=55.0
        )
        # Allow target obliquity to be between 0 (normal) and 60 [deg]
        self.verifyStringVarFloat(
            self.obliquity,
            treshold=0.0,
            maximum=60.0
        )
        # Allow projectile initial velocity to be between 100.0 and 2000.0 [m/s]
        self.verifyStringVarFloat(
            self.velocity,
            treshold=100.0,
            maximum=2000.0
        )
        # Allow element size to be between 0.05 and 2.0 [mm]
        self.verifyStringVarFloat(
            self.elementSize,
            treshold=0.05,
            maximum=2.0
        )

    # Verify if StringVar's value is valid float and fits in limits
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

    # Set GUI title, layout, window size
    def configureAuxiliary(self):
        self.master.title("Armor impact menu")
        self.master.columnconfigure(
            0,
            weight=1
        )
        self.master.rowconfigure(
            0,
            weight=1
        )
        self.frame.grid(
            row=0,
            column=1,
            sticky='NW'
        )
        self.layup.grid(
            row=1,
            column=1,
            sticky='NW'
        )
        # Minimum window size
        self.master.minsize(400, 700)

    # Set entries' layout
    def configureEntries(self):
        self.projectileField.grid(
            column=1,
            row=1,
            sticky='NW'
        )
        self.velocityField.grid(
            column=1,
            row=2,
            sticky='NW'
        )
        self.radiusField.grid(
            column=1,
            row=4,
            sticky='NW'
        )
        self.obliquityField.grid(
            column=1,
            row=5,
            sticky='NW'
        )
        self.layersCountField.grid(
            column=1,
            row=6,
            sticky='NW'
        )
        self.meshElementSizeField.grid(
            column=1,
            row=8,
            sticky='NW'
        )
        self.modelNameField.grid(
            column=1,
            row=10,
            sticky='NW'
        )

    # Set labels' layout
    def configureLabels(self):
        self.projecileMainLabel.grid(
            column=0,
            row=0,
            sticky='NW'
        )
        self.projectileLabel.grid(
            column=0,
            row=1,
            sticky='NW'
        )
        self.velocityLabel.grid(
            column=0,
            row=2,
            sticky='NW'
        )
        self.armorMainLabel.grid(
            column=0,
            row=3,
            sticky='NW'
        )
        self.armorRadiusLabel.grid(
            column=0,
            row=4,
            sticky='NW'
        )
        self.armorObliquityLabel.grid(
            column=0,
            row=5,
            sticky='NW'
        )
        self.armorLayersLabel.grid(
            column=0,
            row=6,
            sticky='NW'
        )
        self.modelMainLabel.grid(
            column=0,
            row=7,
            sticky='NW'
        )
        self.meshElementSize.grid(
            column=0,
            row=8,
            sticky='NW'
        )
        self.modelLabel.grid(
            column=0,
            row=9,
            sticky='NW'
        )
        self.modelNameLabel.grid(
            column=0,
            row=10,
            sticky='NW'
        )
        self.layerNoLabel.grid(
            column=0,
            row=0,
            sticky='NW'
        )
        self.materialLabel.grid(
            column=1,
            row=0,
            sticky='NW'
        )
        self.layerThicknessLabel.grid(
            column=2,
            row=0,
            sticky='NW'
        )
        self.layerSpacingLabel.grid(
            column=3,
            row=0,
            sticky='NW'
        )

    # Generate model configuration object that may be both saved to file or passed to kernel
    def prepareModelConfig(self):
        config = {}
        layers = []
        for (label, matvar, material, thickvar, thickness, spacevar, spacing) in self.layupWidgets:
            layers.append(
                {
                'material': matvar.get(),
                # Convert [mm] to [m]
                'thickness': float(thickvar.get()) / 1000.0,
                'spacing': float(spacevar.get()) / 1000.0
                }
            )
        config['projectile'] = {
            'type': self.projectile.get(),
            # Leave [m/s] as-is
            'velocity': float(self.velocity.get()),
        }
        config['armor'] = {
            # Convert [mm] to [m]
            'radius': float(self.radius.get()) / 1000.0,
            # Leave [deg] as-is
            'obliquity': float(self.obliquity.get()),
            'layers': layers
        }
        # Convert [mm] to [m]
        config['meshElementSize'] = float(self.elementSize.get()) / 1000.0
        return config

    # Load model from configuration object and set entries to proper values
    def loadModelFromConfig(self, config):
        if 'projectile' in config:
            if 'type' in config['projectile']:
                if config['projectile']['type'] in self.parts():
                    self.projectile.set(config['projectile'][u'type'])
            if 'velocity' in config['projectile']:
                # Leave [m/s] as-is
                self.velocity.set(
                    round(
                        float(
                            config['projectile']['velocity']
                        ),
                        1)
                )
        if 'armor' in config:
            if 'radius' in config['armor']:
                # Convert [m] back to [mm]
                self.radius.set(
                    round(
                        float(
                            config[u'armor'][u'radius']
                        ) * 1000.0,
                        1
                    )
                )
            # Currently innerRadius value is ignored
            if 'innerRadius' in config['armor']:
                pass
            if 'obliquity' in config['armor']:
                # Leave [deg] as-is
                self.obliquity.set(
                    round(
                        float(
                            config['armor']['obliquity']
                        ),
                        1
                    )
                )
            if 'layers' in config['armor']:
                self.loadLayersFromConfig(config['armor']['layers'])
        if 'meshElementSize' in config:
            # Convert [m] back to [mm]
            self.elementSize.set(
                round(
                    float(
                        config['meshElementSize']
                    ) * 1000.0,
                    3
                )
            )
        self.verifyFloats()

    # Load target layers from config object section
    def loadLayersFromConfig(self, layers):
        # Clear layers controls
        self.adjustLayup(0)
        # Adjust layers controls to actual number of layers
        self.layersCount.set(len(layers))
        self.adjustLayup(len(layers))
        i = 0
        for layer in layers:
            # Default material is none
            material = ""
            # Default thickness is 0.5 [mm]
            thickness = 0.5
            if 'material' in layer and layer['material'] in self.materials():
                material = layer['material']
            if 'thickness' in layer:
                # Convert [m] to [mm]
                thickness = round(
                    float(
                        layer['thickness']
                    ) * 1000.0,
                    2
                )
            if 'spacing' in layer:
                # Convert [m] to [mm]
                spacing = round(
                    float(
                        layer['spacing']
                    ) * 1000,
                    2
                )
            row = self.layupWidgets[i]
            i += 1
            # Set StringVars to proper values
            row[1].set(material)
            row[3].set(thickness)
            row[5].set(spacing)

# Import parts from Parts folder subdirectories
def importParts(modelName="Model-1"):
    # Clear list of available parts
    del availableParts[:]
    # Make sure Parts directory exists or create one
    __directory = os.path.dirname(os.path.realpath(__file__)) + "\\Parts\\"
    if not os.path.exists(__directory):
        os.makedirs(__directory)
    # List subdirectories
    directories = os.listdir(__directory)
    for __dir in directories:
        name = __dir
        __dir = __directory + __dir
        if os.path.isdir(__dir):
            # Open part file
            projectile = __dir + "\\Projectile.sat"
            projectile = mdb.openAcis(projectile)
            # Open part configuration describing part material and ID in AcisFile
            config = __dir + "\\elements.cfg"
            config = json.load(
                open(config)
            )
            # Create casing and assign it material
            casing = mdb.models[modelName].PartFromGeometryFile(
                "Casing_" + name,
                projectile,
                THREE_D,
                DEFORMABLE_BODY,
                bodyNum=config['casing']['id']
            )
            cells = casing.cells.getSequenceFromMask(
                mask=
                (
                    '[#1 ]',
                ),
            )
            region = casing.Set(
                cells=cells,
                name='volume'
            )
            section = mdb.models[modelName].HomogeneousSolidSection(
                "Casing_" + name,
                str(config['casing']['material'])
            )
            casing.SectionAssignment(
                sectionName="Casing_" + name,
                region=region,
            )
            # Create core and assign it material
            core = mdb.models[modelName].PartFromGeometryFile(
                "Core_" + name,
                projectile,
                THREE_D,
                DEFORMABLE_BODY,
                bodyNum=config['core']['id']
            )
            cells = core.cells.getSequenceFromMask(
                mask=
                (
                    '[#1 ]',
                ),
            )
            region = core.Set(
                cells=cells,
                name='volume'
            )
            section = mdb.models[modelName].HomogeneousSolidSection(
                "Core_" + name,
                str(config['core']['material'])
            )
            core.SectionAssignment(
                sectionName="Core_" + name,
                region=region,
            )
            # Append subdirectory's name to available parts list
            availableParts.append(name)

# Import materials to model
def importMaterials(modelName ="Model-1"):
    # Make sure Materials directory exists
    __directory = os.path.dirname(os.path.realpath(__file__)) + "\\Materials\\"
    if not os.path.exists(__directory):
        os.makedirs(__directory)
    # List all files in directory
    directory = os.listdir(__directory)
    materials = []
    for file in directory:
        # Import all materials from all material libraries
        if file.endswith(".lib"):
            f = open(
                __directory + "\\" + file,
                'r'
            )
            # Unpickle library file
            lib = Unpickler(f).load()
            f.close()
            for (a, b, name, c, mat) in lib:
                # Create materials from actual material datastrings
                if b != -1:
                    createMaterialFromDataString(
                        modelName,
                        mat['Vendor material name'],
                        mat['version'],
                        mat['Data']
                    )
    return materials

# Adjust Abaqus GUI to be less demanding and run plugin's GUI
def __startWindow():
    session.graphicsOptions.setValues(
        highlightMethodHint=XOR,
        antiAlias=OFF,
        translucencyMode=1
    )
    # session.journalOptions.setValues(replayGeometry=INDEX)
    gui = ImpactTestGUI()

# Import materials, then parts, then create plugin's GUI window
def run():
    importMaterials()
    importParts()
    __startWindow()

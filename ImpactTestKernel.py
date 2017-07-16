from abaqus import mdb, session
import part
from abaqusConstants import *

class ImpactTestKernel():
    def __init__(self, config):
        self.projectileType = config['projectile']['type']
        self.projectileVelocity = config['projectile']['velocity']
        self.targetObliquity = config['armor']['obliquity']
        self.targetRadius = config['armor']['radius']
        self.targetLayers = config['armor']['layers']
        self.meshElementSize = config['meshElementSize']

    def run(self):
        self.createTargetPart()
        self.setModelConstants()
        self.createCompositeLayup()
        self.createModelAssembly()
        self.createProjectileMesh()
        self.createTargetMesh()
        self.createProjetileSurfaceSets()
        self.createTargetSurfaceSets()
        self.createInteractionProperties()
        self.setInteractions()
        self.applyInitialFields()
        self.applyBoundaryConditions()
        self.adjustOutputs()
        self.createStep()
        self.createJob()

    def setModelConstants(self):
        pass

    def createTargetPart(self):
        self.__createTargetSketch()
        part = mdb.models['Model-1'].Part('Target', dimensionality=THREE_D, type=DEFORMABLE_BODY)
        part.BaseSolidExtrude(mdb.models['Model-1'].sketches['Target-Sketch'], self.__calculateTargetThickness())
        mdb.models['Model-1'].parts['Target'].DatumCsysByDefault(CARTESIAN)
        mdb.models['Model-1'].parts['Target'].MaterialOrientation(
            stackDirection=STACK_3,
            localCsys=mdb.models['Model-1'].parts['Target'].datums.values()[0]
        )

    def createModelAssembly(self):
        pass

    def createJob(self):
        pass

    def createStep(self):
        pass

    def adjustOutputs(self):
        pass

    def applyBoundaryConditions(self):
        pass

    def applyInitialFields(self):
        pass

    def setInteractions(self):
        pass

    def createInteractionProperties(self):
        pass

    def createTargetSurfaceSets(self):
        pass

    def createProjetileSurfaceSets(self):
        pass

    def createTargetMesh(self):
        pass

    def createProjectileMesh(self):
        pass

    def createCompositeLayup(self):
        layup = mdb.models['Model-1'].parts['Target'].CompositeLayup('Layup', elementType=SOLID)
        layup.setValues(orientation=mdb.models['Model-1'].parts['Target'].datums.values()[0])

    def __createTargetSketch(self):
        sketch = mdb.models['Model-1'].ConstrainedSketch('Target-Sketch', self.targetRadius*2.0)
        sketch.CircleByCenterPerimeter(center=(0.0, 0.0), point1=(0.0, self.targetRadius))

    def __calculateTargetThickness(self):
        thickness = 0.0
        for layer in self.targetLayers:
            thickness += layer['thickness']
        return thickness

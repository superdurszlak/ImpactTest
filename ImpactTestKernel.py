from abaqus import mdb, session
import part

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
        mdb.models['Model-1'].Part('Target')

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
        pass
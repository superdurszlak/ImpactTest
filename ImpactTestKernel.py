from abaqus import mdb, session
import part
from abaqusConstants import *
import regionToolset

class ImpactTestKernel():
    def __init__(self, config):
        self.projectileType = config['projectile']['type']
        self.projectileVelocity = config['projectile']['velocity']
        self.targetObliquity = config['armor']['obliquity']
        self.targetRadius = config['armor']['radius']
        self.targetLayers = config['armor']['layers']
        self.meshElementSize = config['meshElementSize']
        self.assemblyOrder = []

    def run(self):
        self.setModelConstants()
        self.createTargetParts()
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

    def createTargetParts(self):
        self.__createTargetSketch()
        i = 1
        for layer in self.targetLayers:
            name = 'Target-L'+str(i).zfill(3)
            part = mdb.models['Model-1'].Part(name, dimensionality=THREE_D, type=DEFORMABLE_BODY)
            part.BaseSolidExtrude(mdb.models['Model-1'].sketches['Target-Sketch'], layer['thickness'])
            part.DatumCsysByDefault(CARTESIAN)
            part.ReferencePoint(point=part.InterestingPoint(edge=part.edges[0], rule=CENTER))
            section = mdb.models['Model-1'].HomogeneousSolidSection(name, str(layer['material']))
            part.SectionAssignment(
                sectionName=name,
                region=regionToolset.Region(
                    cells=part.cells.getSequenceFromMask(
                        mask=('[#1 ]', ),
                    )
                )
            )
            i += 1
            self.assemblyOrder.append((name, layer['thickness']))


    def createModelAssembly(self):
        assembly = mdb.models['Model-1'].rootAssembly
        assembly.DatumCsysByDefault(CARTESIAN)
        offset = 0.0
        for element in self.assemblyOrder:
            name = element[0]
            thickness = element[1]
            offset -= thickness
            part = mdb.models['Model-1'].parts[name]
            instance = assembly.Instance(name=name, part=part, dependent=ON)
            assembly.translate(instanceList=(name, ), vector=(0.0, 0.0, offset))

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

    def __createTargetSketch(self):
        sketch = mdb.models['Model-1'].ConstrainedSketch('Target-Sketch', self.targetRadius*2.0)
        sketch.CircleByCenterPerimeter(center=(0.0, 0.0), point1=(0.0, self.targetRadius))

    def __calculateTargetThickness(self):
        thickness = 0.0
        for layer in self.targetLayers:
            thickness += layer['thickness']
        return thickness

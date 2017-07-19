from abaqus import mdb, session
import part, mesh
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
            self.__partitionTargetLayer(part, layer['thickness'])


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
        for element in self.assemblyOrder:
            name = element[0]
            part = mdb.models['Model-1'].parts[name]
            session.viewports['Viewport: 1'].setValues(displayedObject=part)
            session.viewports['Viewport: 1'].partDisplay.setValues(mesh=ON)
            elements = part.elements
            elements = elements.getByBoundingBox(
                -self.targetRadius-0.001,
                -self.targetRadius-0.001,
                -0.001,
                self.targetRadius+0.001,
                self.targetRadius+0.001,
                element[1]+0.001
            )
            part.Surface(face1Elements=elements, name="whole")

    def createProjetileSurfaceSets(self):
        pass

    def createTargetMesh(self):
        for element in self.assemblyOrder:
            name = element[0]
            part = mdb.models['Model-1'].parts[name]
            regions = part.cells.getSequenceFromMask(mask=('[#3 ]', ), )
            part.setMeshControls(regions=regions, technique=STRUCTURED)
            regions = part.cells.getSequenceFromMask(mask=('[#4 ]', ), )
            part.setMeshControls(regions=regions, algorithm=MEDIAL_AXIS)
            part.seedPart(size=self.meshElementSize, deviationFactor=0.1, minSizeFactor=0.1)
            edges = part.edges.getSequenceFromMask(mask=('[#9300 ]', ), )
            part.seedEdgeByNumber(edges=edges, number=30)
            edges = part.edges.getSequenceFromMask(mask=('[#55 ]', ), )
            part.seedEdgeBySize(edges=edges, size=self.meshElementSize*20.0, deviationFactor=0.1)
            elemType1 = mesh.ElemType(elemCode=C3D8RT, elemLibrary=EXPLICIT,
                                      kinematicSplit=AVERAGE_STRAIN, secondOrderAccuracy=OFF,
                                      hourglassControl=ENHANCED, distortionControl=DEFAULT, elemDeletion=ON)
            part.setElementType(regions=(part.cells, ), elemTypes=(elemType1, ))
            part.generateMesh()

    def createProjectileMesh(self):
        pass

    def __createTargetSketch(self):
        sketch = mdb.models['Model-1'].ConstrainedSketch('Target-Sketch', self.targetRadius*2.0)
        sketch.CircleByCenterPerimeter(center=(0.0, 0.0), point1=(0.0, self.targetRadius))
        innerRadius = self.targetRadius/4.0
        innerSketch = mdb.models['Model-1'].ConstrainedSketch('Inner-Sketch', self.targetRadius/2.0)
        innerSketch.CircleByCenterPerimeter(center=(0.0, 0.0), point1=(0.0, innerRadius))

    def __calculateTargetThickness(self):
        thickness = 0.0
        for layer in self.targetLayers:
            thickness += layer['thickness']
        return thickness

    def __partitionTargetLayer(self, part, thickness):
        faces, edges, datums = part.faces, part.edges, part.datums
        transform = part.MakeSketchTransform(
            sketchPlane=faces[1],
            sketchUpEdge=datums[2].axis2,
            sketchPlaneSide=SIDE1,
            origin=(0.0, 0.0, thickness)
        )
        sketch = mdb.models['Model-1'].ConstrainedSketch(
            name='__profile__',
            sheetSize=self.targetRadius/2.0,
            gridSpacing=0.001,
            transform=transform
        )
        geometry, vertices, dimensions, constraints = (
            sketch.geometry,
            sketch.vertices,
            sketch.dimensions,
            sketch.constraints
        )
        sketch.sketchOptions.setValues(decimalPlaces=3)
        sketch.setPrimaryObject(option=SUPERIMPOSE)
        part.projectReferencesOntoSketch(sketch=sketch, filter=COPLANAR_EDGES)
        part = mdb.models['Model-1'].parts[part.name]
        sketch.retrieveSketch(sketch=mdb.models['Model-1'].sketches['Inner-Sketch'])
        faces = part.faces
        pickedFaces = faces.getSequenceFromMask(mask=('[#2 ]', ), )
        edges, datums = part.edges, part.datums
        part.PartitionFaceBySketch(
            sketchUpEdge=datums[2].axis2,
            faces=pickedFaces,
            sketch=sketch
        )
        sketch.unsetPrimaryObject()
        del mdb.models['Model-1'].sketches['__profile__']
        cells = part.cells
        pickedCells = cells.getSequenceFromMask(mask=('[#1 ]', ), )
        edges, datums = part.edges, part.datums
        pickedEdges = (edges[1], )
        part.PartitionCellByExtrudeEdge(
            line=datums[2].axis3,
            cells=pickedCells,
            edges=pickedEdges,
            sense=REVERSE
        )
        part.DatumPlaneByPrincipalPlane(principalPlane=YZPLANE, offset=0.0)
        cells = part.cells
        pickedCells = cells.getSequenceFromMask(mask=('[#1 ]', ), )
        datums = part.datums
        part.PartitionCellByDatumPlane(datumPlane=datums[7], cells=pickedCells)


